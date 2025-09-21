"""Clean reconciliation API (replacement blueprint) with metrics & persistence.

Activate by setting environment variable RECONCILIACION_CLEAN=1 so server imports
this module instead of legacy corrupted one.

Features:
  - Endpoints: suggest, sugerencias (alias), preview, confirmar, historial, status, healthz
  - Metrics: rolling latency summary (count,sum,avg,p95) + manual histogram + SLO p95
  - Engine outcome counters (success/fallback/error/empty) with ratios
  - Persistence of latencies (JSON + optional gzip) with adaptive threshold
  - Prometheus text exposition + optional prometheus_client endpoint
  - Metrics reset + debug endpoints (latencies & snapshot) gated by flags

Env vars (optional):
  RECON_DISABLE_METRICS=1
  RECON_LATENCY_BUCKETS="0.005,0.01,0.05"  (seconds)
  RECON_LATENCY_SLO_P95=0.25
  RECON_LATENCY_PERSIST_PATH=/path/latencies.json[.gz]
  RECON_LATENCY_PERSIST_COMPRESS=1
  RECON_LATENCY_PERSIST_COMPRESS_MIN_BYTES=4096
  RECON_LATENCY_PERSIST_EVERY_N=25
  RECON_LATENCY_PERSIST_INTERVAL_SEC=30
  RECON_METRICS_RESET_TOKEN=secret
  RECON_METRICS_DEBUG=1
  RECON_METRICS_DEBUG_TOKEN=secret
  RECON_PROM_CLIENT=1
"""
from __future__ import annotations

from collections import deque
from queue import Queue, Empty
import gzip
import random  # may still be used for sampling decision
import re
import json
import math
import os
import time
import threading
import hashlib
import atexit
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.metrics_utils import percentile, histogram, compute_latency_summary
from backend.config_validation import validate_environment  # type: ignore

from flask import Blueprint, jsonify, request, current_app
from backend import reconcile_adapter
from backend import legacy_compat  # new legacy helpers

from backend.db_utils import db_conn  # type: ignore
from backend.recon_constants import (  # type: ignore
    SUGGEST_MIN_LIMIT,
    SUGGEST_MAX_LIMIT,
    SUGGEST_DEFAULT_LIMIT,
)

bp = Blueprint("conciliacion", __name__)


# In-memory state
def _initial_window_size() -> int:
    try:
        v = int(os.environ.get("RECON_LATENCY_WINDOW_SIZE", "500") or 500)
        return max(50, min(10_000, v))
    except Exception:
        return 500


_LATENCIES: deque[float] = deque(maxlen=_initial_window_size())
_REQ_TS: deque[float] = deque(maxlen=_LATENCIES.maxlen)
_RESET_TS = time.time()
_DEFAULT_BUCKETS = (0.005, 0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1.0)
_SLO_VIOLATIONS = 0
_ENG_SUCCESS = 0
_ENG_FALLBACK = 0
_ENG_ERROR = 0
_ENG_EMPTY = 0
_PERSIST_LAST = 0.0
_PERSIST_PENDING = 0
_PERSIST_FLUSHES = 0
_PERSIST_LAST_SIZE = 0  # compressed or plain on disk
_PERSIST_LAST_RAW_SIZE = 0  # size before compression
_PERSIST_ERRORS = 0
_RECON_RECONCILIATIONS_TOTAL = 0  # legacy-style counter for metrics compatibility
_RECON_LINKS_TOTAL = 0  # legacy-style counter
_ALIAS_LEN_VIOLATIONS = 0  # count of times alias was truncated
_ALIAS_MAX_LEN = 120

# --- Legacy compatibility aliases (tests expect these names) ---
# The legacy test suite refers to *_SUGGEST_* symbols and a loader function
# named `_load_persisted_latencies`. We provide thin aliases that stay in
# sync with the primary state so newer code keeps using the modern names.
_SUGGEST_LATENCIES = _LATENCIES  # deque reference (will be re-bound on reset)
_SUGGEST_SLO_VIOLATION_TOTAL = _SLO_VIOLATIONS
_SUGGEST_LAT_LAST_RESET = _RESET_TS
_LAST_SAMPLE_VIOLATION = 0  # 1 if last recorded sample violated p95 SLO

# Concurrency lock (lightweight) to avoid torn writes on multi-threaded WSGI
_LOCK = threading.RLock()


# ---------------- Legacy style loader (tests call _load_persisted_latencies) --------------
def _load_persisted_latencies() -> None:  # legacy test helper (now wrapper)
    _load_any_persisted(priority_legacy=True)


# Explicitly declare these names as module-level for clarity (import error guard)
__all_counters__ = [
    '_RECON_RECONCILIATIONS_TOTAL', '_RECON_LINKS_TOTAL', '_ALIAS_LEN_VIOLATIONS', '_ALIAS_MAX_LEN'
]


def suggest_for_movement(context: str, movement_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Compatibility helper used by legacy tests to fetch suggestions."""
    payload = {"id": movement_id}
    try:
        results = reconcile_adapter.suggest(context or "bank", payload)
    except Exception:
        return []
    if limit is not None:
        return results[:limit]
    return results


# ---------------- Env helpers ----------------

def _e_bool(k: str) -> bool:
    return os.environ.get(k, "").strip().lower() in {"1", "true", "yes", "on"}


def _e_int(k: str, default: int) -> int:
    try:
        return int(os.environ.get(k, "") or default)
    except ValueError:
        return default


def _e_float(k: str, default: float) -> float:
    try:
        return float(os.environ.get(k, "") or default)
    except ValueError:
        return default


def _persist_path() -> Optional[str]:
    return os.environ.get("RECON_LATENCY_PERSIST_PATH") or None


def _persist_every_n() -> int:
    # Legacy behaviour flushed every sample by default; tests rely on immediate flush.
    # RECON_FAST_MODE permite elevar el valor para reducir IO.
    fast = _e_bool("RECON_FAST_MODE")
    base = _e_int("RECON_LATENCY_PERSIST_EVERY_N", 1)
    if fast and base == 1:
        return 5
    return max(1, base)


def _persist_interval() -> float:
    return max(1.0, _e_float("RECON_LATENCY_PERSIST_INTERVAL_SEC", 60.0))


def _persist_force_gzip() -> bool:
    return _e_bool("RECON_LATENCY_PERSIST_COMPRESS")


def _persist_min_bytes() -> int:
    return _e_int("RECON_LATENCY_PERSIST_COMPRESS_MIN_BYTES", 4096)


def _latency_buckets() -> List[float]:
    raw = os.environ.get("RECON_LATENCY_BUCKETS")
    if not raw:
        return list(_DEFAULT_BUCKETS)
    vals: List[float] = []
    for part in raw.split(','):
        part = part.strip()
        if not part:
            continue
        try:
            v = float(part)
        except ValueError:
            continue
        if v > 0:
            vals.append(v)
    vals = sorted(set(vals))
    return vals or list(_DEFAULT_BUCKETS)


def _slo_target() -> float:
    return max(0.0, _e_float("RECON_LATENCY_SLO_P95", 0.0))


def _metrics_disabled() -> bool:
    """Return True if metrics should be disabled.

    Dual env var support (backwards compatibility):
      RECON_DISABLE_METRICS=1        -> disable
      RECON_METRICS_DISABLED=1|true  -> disable (legacy name)
      RECON_METRICS_DISABLED=false   -> FORCE ENABLE (override any disable flag)

    Rationale: Some older tests toggle only RECON_METRICS_DISABLED and expect that
    setting it to 'false' re-enables metrics even if a previous test set
    RECON_DISABLE_METRICS=1 in the same Python process. To remove order
    dependence we treat the explicit legacy 'false' as an override that clears
    the disable condition.
    """
    legacy_raw = os.environ.get("RECON_METRICS_DISABLED", "").strip().lower()
    if legacy_raw in {"false", "0", "no", "off"}:
        return False  # explicit override: force enabled
    disable_flag = _e_bool("RECON_DISABLE_METRICS")
    legacy_flag = legacy_raw in {"1", "true", "yes", "on"}
    return disable_flag or legacy_flag


def _prom_client_enabled() -> bool:
    return _e_bool("RECON_PROM_CLIENT")


def _structured_logging_enabled() -> bool:
    # Runtime override (in-memory) can force enable/disable irrespective of env
    forced = _RUNTIME_OVERRIDES.get("structured_logs_enabled")
    if forced is not None:
        return bool(forced)
    return _e_bool("RECON_STRUCTURED_LOGS") or _test_mode_enabled()


def _async_logging_enabled() -> bool:
    if not _structured_logging_enabled():
        return False
    forced = _RUNTIME_OVERRIDES.get("async_enabled")
    if forced is not None:
        return bool(forced)
    return _e_bool("RECON_STRUCTURED_LOG_ASYNC")


def _ensure_async_worker():  # pragma: no cover (best effort thread)
    global _ASYNC_QUEUE, _ASYNC_THREAD, _ASYNC_STOP
    if not _async_logging_enabled():
        return
    if _ASYNC_QUEUE is None:
        maxsize = _e_int("RECON_STRUCTURED_LOG_ASYNC_QUEUE", 1000)
        _ASYNC_QUEUE = Queue(maxsize=max(10, maxsize))
    if _ASYNC_THREAD is None or not _ASYNC_THREAD.is_alive():
        # Capture logger reference to avoid depending on Flask context inside thread
        try:
            logger_ref = current_app.logger  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover
            logger_ref = None

        queue_ref = _ASYNC_QUEUE  # capture stable reference to avoid race if global cleared

        def _worker():  # noqa: ANN001
            global _ASYNC_STOP, _EMIT_FAILURES_TOTAL
            while True:
                # Exit condition: requested stop AND queue empty (or queue missing)
                if _ASYNC_STOP and (queue_ref is None or queue_ref.empty()):
                    break
                if queue_ref is None:
                    time.sleep(0.05)
                    continue
                try:
                    item = queue_ref.get(timeout=0.25)
                except Empty:
                    continue
                if item is None:
                    continue
                _, rec = item
                try:
                    if logger_ref is not None:
                        logger_ref.info(json.dumps(rec, sort_keys=True, ensure_ascii=False))
                    else:  # fallback: attempt using current_app
                        current_app.logger.info(json.dumps(rec, sort_keys=True, ensure_ascii=False))  # type: ignore[attr-defined]
                except Exception:
                    _EMIT_FAILURES_TOTAL += 1
        _ASYNC_STOP = False
        _ASYNC_THREAD = threading.Thread(target=_worker, name="recon-structlog", daemon=True)
        _ASYNC_THREAD.start()
        # Register flush at exit (best-effort)
        
        def _flush_at_exit():  # pragma: no cover
            global _ASYNC_STOP
            _ASYNC_STOP = True
            if _ASYNC_QUEUE is not None:
                deadline = time.time() + 1.0
                while not _ASYNC_QUEUE.empty() and time.time() < deadline:
                    try:
                        time.sleep(0.01)
                    except Exception:
                        break
        atexit.register(_flush_at_exit)


def _current_request_id() -> str:
    # Prefer inbound header, else generate short random token.
    try:
        rid = request.headers.get("X-Request-Id")  # type: ignore[attr-defined]
    except Exception:
        rid = None
    if rid:
        return rid[:64]
    # fallback: time-based entropy
    return f"req-{int(time.time()*1000):x}-{os.getpid():x}"


SCHEMA_VERSION = 1  # structured log schema version; bump on breaking changes


_EMITTED_EVENTS_TOTAL = 0
_SAMPLED_OUT_EVENTS_TOTAL = 0
_EMIT_FAILURES_TOTAL = 0  # count of structured log primary emission failures (before fallback)
_LAST_STRUCTURED_EVENT_TS: float = 0.0  # wall clock seconds of last (attempted) emitted structured event
_ASYNC_QUEUE = None  # queue.Queue when async enabled
_ASYNC_THREAD = None  # threading.Thread worker
_ASYNC_DROPPED = 0  # number of events dropped due to full queue
_ASYNC_STOP = False  # signal for worker termination (not currently exposed)

# ---------------- Runtime overrides (in-memory, non-persistent) ----------------
# Keys:
#   global_sample_rate: Optional[float] within [0,1]
#   per_event_sample: Dict[event_token->rate]
#   structured_logs_enabled: Optional[bool]
#   async_enabled: Optional[bool]
_RUNTIME_OVERRIDES: Dict[str, Any] = {
    # example structure; empty means no overrides
}


# Redaction: comma separated list of fields to drop from structured events (non-core only)
_REDACT_CORE = {"event", "request_id", "timestamp", "schema_version"}


def _redact_fields() -> set[str]:
    raw = os.environ.get("RECON_STRUCTURED_REDACT", "").strip()
    if not raw:
        return set()
    out = set()
    for part in raw.split(','):
        p = part.strip()
        if not p:
            continue
        if p in _REDACT_CORE:
            continue  # never redact core fields
        out.add(p)
    return out


# Debug flags: comma separated list of tokens echoed (array) on each structured event.
def _debug_flags() -> List[str]:
    raw = os.environ.get("RECON_DEBUG_FLAGS", "").strip()
    if not raw:
        return []
    flags: List[str] = []
    seen = set()
    for part in raw.split(','):
        p = part.strip()
        if not p:
            continue
        if p in seen:
            continue
        seen.add(p)
        flags.append(p[:64])  # cap length defensively
    return flags
# (blank lines maintained below for style)


# Event schema metadata (for /api/conciliacion/logs/schema endpoint)
_EVENT_SCHEMA: Dict[str, Dict[str, Any]] = {
    "recon_suggest_request": {
        "required": ["event", "request_id", "timestamp", "schema_version", "outcome"],
        "optional": [
            "context", "movement_id", "limit", "latency_seconds", "latency_window",
            "slo_p95_target", "slo_violations_total", "window_size", "sample_count", "debug_flags"
        ],
        "description": "Suggest endpoint invocation summary and rolling latency snapshot"
    },
    "recon_confirmar_request": {
        "required": ["event", "request_id", "timestamp", "schema_version", "variant", "accepted"],
        "optional": [
            "context", "movement_id", "reconciliation_id", "confidence", "links_count",
            "alias_present", "alias_truncated", "debug_flags"
        ],
        "description": "Confirmar endpoint usage (multiple path variants)"
    },
    "recon_metrics_reset": {
        "required": ["event", "request_id", "timestamp", "schema_version", "before", "after"],
        "optional": [
            "ok", "reset_at", "slo_violation_total_before", "slo_violation_total_after", "buckets", "debug_flags"
        ],
        "description": "Metrics window reset event"
    },
    "recon_log_emit_error": {
        "required": ["event", "request_id", "timestamp", "schema_version", "original_event", "exception_class"],
        "optional": ["message", "redacted_fields_attempted"],
        "description": "Fallback emission when structured event serialization fails"
    }
}


def _emit_structured(event: str, payload: Dict[str, Any]) -> None:
    if not _structured_logging_enabled():
        return
    global _EMITTED_EVENTS_TOTAL, _SAMPLED_OUT_EVENTS_TOTAL, _EMIT_FAILURES_TOTAL
    try:
        # Determine base global sample rate
        global_raw = os.environ.get("RECON_STRUCTURED_LOG_SAMPLE")

        def _parse_rate(val: Optional[str]) -> Optional[float]:
            if val is None:
                return None
            try:
                r = float(val)
            except Exception:
                return None
            if 0.0 <= r <= 1.0:
                return r
            return None

        override_rate = _RUNTIME_OVERRIDES.get("global_sample_rate")
        if override_rate is not None:
            try:
                orf = float(override_rate)
                if 0.0 <= orf <= 1.0:
                    global_rate = orf
                else:
                    global_rate = 1.0
            except Exception:
                global_rate = 1.0
        else:
            global_rate = _parse_rate(global_raw) or 1.0

        # Per-event sampling override
        raw_event_key = re.sub(r"[^A-Za-z0-9]", "_", event).upper()
        per_event_env = f"RECON_STRUCTURED_LOG_SAMPLE_{raw_event_key}"
        override_rate_env = _parse_rate(os.getenv(per_event_env))
        # Runtime per-event overrides map uses the same transformed key token
        override_runtime_map: Dict[str, float] = _RUNTIME_OVERRIDES.get("per_event_sample", {}) or {}
        override_runtime = None
        if raw_event_key in override_runtime_map:
            try:
                rr = float(override_runtime_map[raw_event_key])
                if 0.0 <= rr <= 1.0:
                    override_runtime = rr
            except Exception:
                override_runtime = None
        chosen_override = override_runtime if override_runtime is not None else override_rate_env
        sample_rate = chosen_override if chosen_override is not None else global_rate

        if sample_rate < 1.0 and random.random() > sample_rate:
            _SAMPLED_OUT_EVENTS_TOTAL += 1
            return
        ts = time.time()
        global _LAST_STRUCTURED_EVENT_TS
        _LAST_STRUCTURED_EVENT_TS = ts
        ts_rfc3339 = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts)) + f".{int((ts % 1)*1000):03d}Z"
        rec = {
            "event": event,
            "request_id": _current_request_id(),
            "timestamp": ts_rfc3339,
            "schema_version": SCHEMA_VERSION,
            **payload,
        }
        dbg = _debug_flags()
        if dbg:
            rec["debug_flags"] = dbg
        redact = _redact_fields()
        redacted_count = 0
        if redact:
            for k in list(rec.keys()):
                if k in redact:
                    rec.pop(k, None)
                    redacted_count += 1
        if redacted_count > 0:
            # Include redaction_count so downstream systems can audit removals
            rec["redaction_count"] = redacted_count
        if _async_logging_enabled():
            _ensure_async_worker()
            try:
                if _ASYNC_QUEUE is not None:
                    try:
                        _ASYNC_QUEUE.put_nowait((event, rec))  # type: ignore[arg-type]
                        _EMITTED_EVENTS_TOTAL += 1
                    except Exception:
                        global _ASYNC_DROPPED
                        _ASYNC_DROPPED += 1
                else:  # fallback to direct
                    current_app.logger.info(json.dumps(rec, sort_keys=True, ensure_ascii=False))
                    _EMITTED_EVENTS_TOTAL += 1
            except Exception:
                _EMIT_FAILURES_TOTAL += 1
        else:
            try:
                current_app.logger.info(json.dumps(rec, sort_keys=True, ensure_ascii=False))
                _EMITTED_EVENTS_TOTAL += 1
            except Exception as exc:  # fallback emission with minimal risk of recursion
                _EMIT_FAILURES_TOTAL += 1
                try:
                    ts2 = time.time()
                    ts_rfc3339_2 = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts2)) + f".{int((ts2 % 1)*1000):03d}Z"
                    err_ev = {
                        "event": "recon_log_emit_error",
                        "request_id": rec.get("request_id", _current_request_id()),
                        "timestamp": ts_rfc3339_2,
                        "schema_version": SCHEMA_VERSION,
                        "original_event": event,
                        "exception_class": exc.__class__.__name__,
                        "message": str(exc)[:200],
                        "redacted_fields_attempted": redacted_count,
                    }
                    try:
                        current_app.logger.error(json.dumps(err_ev, sort_keys=True, ensure_ascii=False))
                        _EMITTED_EVENTS_TOTAL += 1
                    except Exception:
                        pass
                except Exception:
                    pass
    except Exception:  # pragma: no cover
        pass

# --------------- Persistence ---------------

 
def _load_any_persisted(priority_legacy: bool = False) -> None:
    """Internal loader used by both legacy test helper and on import.

    priority_legacy: if True tries the exact path (and optional .gz) preserving
    legacy behaviour of skipping alternate compressed/uncompressed second pass.
    """
    global _SLO_VIOLATIONS, _SUGGEST_SLO_VIOLATION_TOTAL, _RESET_TS, _SUGGEST_LAT_LAST_RESET
    path = _persist_path()
    if not path:
        return
    candidates = []
    if priority_legacy:
        if path.endswith('.gz'):
            candidates = (path,)
        else:
            candidates = (path, path + '.gz')
    else:
        candidates = (path, path + '.gz')
    with _LOCK:
        for candidate in candidates:
            p = Path(candidate)
            if not p.exists():
                continue
            try:
                if p.stat().st_size == 0:
                    try:
                        p.unlink()
                    except Exception:
                        pass
                    continue
                if candidate.endswith('.gz'):
                    with gzip.open(p, 'rt', encoding='utf-8') as fh:  # type: ignore[arg-type]
                        data = json.load(fh)
                else:
                    data = json.loads(p.read_text(encoding='utf-8'))
            except Exception as exc:  # pragma: no cover
                try:
                    current_app.logger.warning("persist load failed: %s", exc)
                except Exception:
                    pass
                try:
                    p.unlink()
                except Exception:
                    pass
                return
            # Optional integrity verification for newer snapshots (version + checksum)
            if isinstance(data, dict) and "version" in data and "checksum" in data:
                checksum = data.get("checksum")
                # Recompute checksum excluding the checksum field itself
                copy_no_checksum = {k: v for k, v in data.items() if k != "checksum"}
                try:
                    checksum_src = json.dumps(copy_no_checksum, sort_keys=True, separators=(",", ":"))
                    expected = "sha256:" + hashlib.sha256(checksum_src.encode("utf-8")).hexdigest()
                except Exception:
                    expected = None
                if not checksum or checksum != expected:
                    # Corrupted snapshot -> remove and abort load (leave memory state untouched)
                    try:
                        p.unlink()
                    except Exception:
                        pass
                    return
            # Prepare temp list so we only mutate structures if parse succeeded
            parsed: list[float] = []
            if isinstance(data, dict):
                arr = data.get('latencies', [])
                slo_total = data.get('slo_violation_total') or data.get('slo_p95_violation_total')
                last_reset = data.get('last_reset') or data.get('last_reset_ts')
            else:
                arr = data
                slo_total = None
                last_reset = None
            if isinstance(arr, list):
                for v in arr[-(_LATENCIES.maxlen or len(arr)):]:
                    try:
                        parsed.append(float(v))
                    except Exception:
                        pass
            # Mutate now
            _LATENCIES.clear()
            for v in parsed:
                _LATENCIES.append(v)
            if slo_total is not None:
                try:
                    _SLO_VIOLATIONS = int(float(slo_total))
                except Exception:
                    _SLO_VIOLATIONS = 0
                _SUGGEST_SLO_VIOLATION_TOTAL = _SLO_VIOLATIONS
            if last_reset is not None:
                try:
                    _RESET_TS = float(last_reset)
                except Exception:
                    pass
                _SUGGEST_LAT_LAST_RESET = _RESET_TS
            # Mirror to alias deque (if alias reference differs, copy over)
            if _SUGGEST_LATENCIES is not _LATENCIES:
                try:
                    _SUGGEST_LATENCIES.clear()
                    _SUGGEST_LATENCIES.extend(_LATENCIES)
                except Exception:  # pragma: no cover
                    pass
            return  # load only first existing candidate

 
def _load_persisted() -> None:  # best effort modern path
    # Preserve original alias reference (legacy shim may hold it) and always repopulate it
    alias_ref = _SUGGEST_LATENCIES
    _load_any_persisted(priority_legacy=False)
    if alias_ref is not _LATENCIES:
        # Sync legacy alias deque content with current window
        try:
            alias_ref.clear()
            alias_ref.extend(_LATENCIES)
        except Exception:  # pragma: no cover - defensive
            pass
    # If after load the alias deque is still empty but there is persisted file with data not read (e.g. due to path mismatch), leave as is to keep legacy semantics (empty means no valid snapshot).


def _should_flush(now: float) -> bool:
    if _PERSIST_PENDING <= 0:
        return False
    if _PERSIST_PENDING >= _persist_every_n():
        return True
    # Only consider interval-based flush after first successful flush (avoid immediate flush on first sample)
    if _PERSIST_LAST > 0 and (now - _PERSIST_LAST) >= _persist_interval():
        return True
    return False


def _persist(force: bool = False) -> None:
    path = _persist_path()
    if not path:
        return
    global _PERSIST_LAST, _PERSIST_PENDING, _PERSIST_FLUSHES, _PERSIST_LAST_SIZE, _PERSIST_LAST_RAW_SIZE, _PERSIST_ERRORS
    now = time.time()
    if not force and not _should_flush(now):
        return
    try:
        # Persist extra fields for full restoration + integrity metadata (version + checksum)
        payload = {"version": 1, "ts": now, "latencies": list(_LATENCIES), "slo_violation_total": _SLO_VIOLATIONS, "last_reset": _RESET_TS, "window_capacity": _LATENCIES.maxlen}
        # Compute checksum over deterministic JSON without the checksum field
        checksum_src = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        payload["checksum"] = "sha256:" + hashlib.sha256(checksum_src.encode("utf-8")).hexdigest()
        raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        use_gzip = False
        if _persist_force_gzip() or path.endswith('.gz'):
            use_gzip = True
        elif len(raw) >= _persist_min_bytes():
            use_gzip = True
        target = Path(path if (path.endswith('.gz') or not use_gzip) else path + '.gz')
        if use_gzip:
            tmp = Path(str(target) + '.tmp')
            with gzip.open(tmp, 'wb') as fh:  # type: ignore[arg-type]
                fh.write(raw)
            tmp.replace(target)
        else:
            tmp = Path(str(target) + '.tmp')
            tmp.write_bytes(raw)
            tmp.replace(target)
        _PERSIST_LAST = now
        _PERSIST_PENDING = 0
        _PERSIST_FLUSHES += 1
        _PERSIST_LAST_RAW_SIZE = len(raw)
        try:
            _PERSIST_LAST_SIZE = target.stat().st_size
        except Exception:
            _PERSIST_LAST_SIZE = 0
    except Exception as exc:  # pragma: no cover
        try:
            current_app.logger.warning("persist write failed: %s", exc)
        except Exception:
            pass
        _PERSIST_ERRORS += 1


# --------------- Metrics math ---------------

def _percentile(sorted_vals: List[float], q: float) -> float:  # backward compat wrapper
    return percentile(sorted_vals, q)


def _histogram(values: List[float], buckets: List[float]) -> List[tuple[float, int]]:  # wrapper
    return [(b, c) for b, c in histogram(values, buckets)]


def _record_latency(seconds: float) -> None:
    global _SLO_VIOLATIONS, _PERSIST_PENDING, _LAST_SAMPLE_VIOLATION, _SUGGEST_SLO_VIOLATION_TOTAL, _PERSIST_LAST
    with _LOCK:
        _LATENCIES.append(seconds)
        _REQ_TS.append(time.time())
        _PERSIST_PENDING += 1
        if _PERSIST_LAST == 0.0:  # anchor start so interval flush waits
            _PERSIST_LAST = time.time()
        slo = _slo_target()
        violated = 0
        if slo > 0 and seconds > slo:
            _SLO_VIOLATIONS += 1
            violated = 1
        _LAST_SAMPLE_VIOLATION = violated
        _SUGGEST_SLO_VIOLATION_TOTAL = _SLO_VIOLATIONS
    _persist()


def _latency_summary() -> Dict[str, float]:  # kept broad for legacy callers expecting Dict[str,float]
    res = compute_latency_summary(list(_LATENCIES), _latency_buckets(), _slo_target())
    summary = res["summary"]
    # Cast numeric fields to float for stability (TypedDict already numeric)
    out: Dict[str, float] = {}
    for k, v in summary.items():
        try:
            out[k] = float(v)  # type: ignore[arg-type]
        except Exception:
            continue
    return out


def _utilization(now: float, window: float) -> float:
    cutoff = now - window
    n = sum(1 for t in _REQ_TS if t >= cutoff)
    return round(n / window, 4) if n else 0.0


def _engine_stats() -> Dict[str, float]:
    total = _ENG_SUCCESS + _ENG_FALLBACK + _ENG_ERROR + _ENG_EMPTY

    def ratio(x: int) -> float:
        return round(x / total, 4) if total else 0.0
    return {
        "success_total": float(_ENG_SUCCESS),
        "fallback_total": float(_ENG_FALLBACK),
        "error_total": float(_ENG_ERROR),
        "empty_total": float(_ENG_EMPTY),
        "success_ratio": ratio(_ENG_SUCCESS),
        "fallback_ratio": ratio(_ENG_FALLBACK),
        "error_ratio": ratio(_ENG_ERROR),
        "empty_ratio": ratio(_ENG_EMPTY),
    }


def _metrics_payload() -> Dict[str, Any]:
    now = time.time()
    comp = compute_latency_summary(list(_LATENCIES), _latency_buckets(), _slo_target())
    hist = comp["histogram"]
    hist_payload = []
    for b, c in hist:
        hist_payload.append({"le": b, "cumulative_count": c})
    q_cur = (_ASYNC_QUEUE.qsize() if _ASYNC_QUEUE is not None else 0)
    q_max = (_ASYNC_QUEUE.maxsize if _ASYNC_QUEUE is not None else 0)
    q_util = (q_cur / q_max) if q_max else 0.0
    override_count = sum(1 for k in _RUNTIME_OVERRIDES.keys() if k in {"global_sample_rate", "per_event_sample", "structured_logs_enabled", "async_enabled"})
    drop_ratio = (_ASYNC_DROPPED / (_EMITTED_EVENTS_TOTAL + _ASYNC_DROPPED)) if (_EMITTED_EVENTS_TOTAL + _ASYNC_DROPPED) else 0.0
    return {
        "generated_at": now,
        "uptime": now - _RESET_TS,
        "suggest_latency": _latency_summary(),
        "suggest_latency_histogram": hist_payload,
        "slo_p95_target": _slo_target(),
        "slo_p95_violation_total": _SLO_VIOLATIONS,
        "requests_per_second_60s": _utilization(now, 60.0),
        "requests_per_second_300s": _utilization(now, 300.0),
        "engine": _engine_stats(),
        "structured_logging": {
            "enabled": _structured_logging_enabled(),
            "emitted_total": _EMITTED_EVENTS_TOTAL,
            "sampled_out_total": _SAMPLED_OUT_EVENTS_TOTAL,
            "emit_failures_total": _EMIT_FAILURES_TOTAL,
            "schema_version": SCHEMA_VERSION,
            "async_enabled": _async_logging_enabled(),
            "queue_dropped_total": _ASYNC_DROPPED,
            "async_queue_current": q_cur,
            "async_queue_max": q_max,
            "async_queue_utilization": q_util,
            "drop_ratio": drop_ratio,
            "overrides_active_count": override_count,
            "failure_ratio": (_EMIT_FAILURES_TOTAL / _EMITTED_EVENTS_TOTAL) if _EMITTED_EVENTS_TOTAL else 0.0,
        },
        "persist": {
            "path": _persist_path(),
            "pending": _PERSIST_PENDING,
            "last_flush_at": _PERSIST_LAST,
            "every_n": _persist_every_n(),
            "interval": _persist_interval(),
            "flushes": _PERSIST_FLUSHES,
            "compress_min_bytes": _persist_min_bytes(),
            "force_compress": _persist_force_gzip(),
            "last_size_bytes": _PERSIST_LAST_SIZE,
            "last_raw_bytes": _PERSIST_LAST_RAW_SIZE,
            "compression_ratio": (float(_PERSIST_LAST_SIZE)/_PERSIST_LAST_RAW_SIZE) if _PERSIST_LAST_RAW_SIZE else 0.0,
            "errors": _PERSIST_ERRORS,
        },
        "window_size": _LATENCIES.maxlen,
    }


def _prom_text(payload: Dict[str, Any]) -> str:
    s = payload["suggest_latency"]  # already summary from compute_latency_summary
    lines: List[str] = []
    lines.append("# HELP recon_suggest_latency_seconds Summary (count,sum,avg,p50,p95,p99)")
    lines.append("# TYPE recon_suggest_latency_seconds summary")
    lines.append(f'recon_suggest_latency_seconds_count {int(s["count"])}')
    lines.append(f'recon_suggest_latency_seconds_sum {s["sum"]:.9f}')
    lines.append(f'recon_suggest_latency_seconds_avg {s["avg"]:.9f}')
    lines.append(f'recon_suggest_latency_seconds_p50 {s["p50"]:.9f}')
    lines.append(f'recon_suggest_latency_seconds_p95 {s["p95"]:.9f}')
    lines.append(f'recon_suggest_latency_seconds_p99 {s["p99"]:.9f}')
    # Legacy histogram naming expected by tests: recon_suggest_latency_seconds_histogram_bucket
    lines.append("# HELP recon_suggest_latency_seconds_histogram_bucket Histogram cumulative counts")
    lines.append("# TYPE recon_suggest_latency_seconds_histogram_bucket histogram")
    for b in payload["suggest_latency_histogram"]:
        le = b["le"]
        label = "+Inf" if math.isinf(le) else f"{le:.3f}".rstrip('0').rstrip('.') if not math.isinf(le) else "+Inf"
        lines.append(f'recon_suggest_latency_seconds_histogram_bucket{{le="{label}"}} {b["cumulative_count"]}')
    lines.append(f'recon_suggest_latency_seconds_histogram_bucket_total {int(s["count"])}')
    # SLO / violation gauges + ratios
    lines.append(f'recon_suggest_latency_p95_slo {payload["slo_p95_target"]:.9f}')
    lines.append(f'recon_suggest_latency_p95_violation_total {int(payload["slo_p95_violation_total"])}')
    ratio = 0.0
    if s["count"]:
        ratio = payload["slo_p95_violation_total"] / s["count"]
    lines.append(f'recon_suggest_latency_p95_violation_ratio {ratio:.9f}')
    lines.append(f'recon_suggest_latency_p95_violation {_LAST_SAMPLE_VIOLATION}')
    # Window metrics
    lines.append(f'recon_suggest_latency_window_size {int(s["count"])}')
    lines.append(f'recon_suggest_latency_window_capacity {_LATENCIES.maxlen}')
    util_percent = 0.0
    if _LATENCIES.maxlen:
        util_percent = (s["count"] / _LATENCIES.maxlen) * 100.0
    lines.append(f'recon_suggest_latency_window_utilization_percent {util_percent:.6f}')
    lines.append(f'recon_suggest_latency_last_reset_timestamp {_RESET_TS:.6f}')
    lines.append(f'recon_persist_last_flush_timestamp {_PERSIST_LAST:.6f}')
    # Requests per minute (simple approximation from 60s utilization)
    # Derive rpm from actual request timestamps to avoid rounding drift.
    now = time.time()
    count_60 = sum(1 for t in _REQ_TS if t >= now - 60.0)
    rpm = count_60  # since window < 60s during tests, count approximates rpm expectation
    lines.append(f'recon_suggest_requests_per_minute {float(rpm):.6f}')
    # Snapshot age (file mtime if exists else 0)
    snap_path = _persist_path()
    age = 0.0
    if snap_path:
        for c in (snap_path, snap_path + '.gz'):
            p = Path(c)
            if p.exists():
                try:
                    age = max(0.0, time.time() - p.stat().st_mtime)
                except Exception:
                    age = 0.0
                break
    lines.append(f'recon_suggest_latency_snapshot_age_seconds {age:.6f}')
    eng = payload["engine"]
    for k in ["success_total", "fallback_total", "error_total", "empty_total"]:
        lines.append(f'recon_engine_{k} {eng[k]}')  # modern
        lines.append(f'recon_suggest_engine_{k} {eng[k]}')  # legacy expected
    for k in ["success_ratio", "fallback_ratio", "error_ratio", "empty_ratio"]:
        lines.append(f'recon_engine_{k} {eng[k]:.6f}')
    # Persistence extras
    persist = payload["persist"]
    lines.append(f'recon_persist_error_total {persist["errors"]}')
    lines.append(f'recon_persist_last_size_bytes {persist["last_size_bytes"]}')
    lines.append(f'recon_persist_last_raw_bytes {persist["last_raw_bytes"]}')
    lines.append(f'recon_persist_last_compression_ratio {persist["compression_ratio"]:.6f}')
    # Legacy prefixed persistence gauges
    lines.append(f'recon_suggest_latency_persist_pending_samples {persist["pending"]}')
    # File size gauge
    lines.append(f'recon_suggest_latency_persist_file_bytes {persist["last_size_bytes"]}')
    # Backward compatibility for violation total (earlier naming pattern)
    lines.append(f'recon_suggest_slo_p95_violation_total {int(payload["slo_p95_violation_total"])}')
    return "\n".join(lines) + "\n"


# --------------- Helpers ---------------

def _coerce_int(v: Any) -> Optional[int]:
    try:
        if v is None:
            return None
        return int(v)
    except Exception:
        return None


def _sanitize_limit(v: Optional[int]) -> int:
    if v is None:
        return SUGGEST_DEFAULT_LIMIT
    return max(SUGGEST_MIN_LIMIT, min(SUGGEST_MAX_LIMIT, v))


# --------------- Routes ---------------

@bp.get("/api/conciliacion/status")
def status():
    cfg = validate_environment()
    return jsonify({
        "status": "disabled" if _metrics_disabled() else "ok",
        "samples": len(_LATENCIES),
        "slo_p95": _slo_target(),
        "engine_available": True,
        "adapter_available": True,
        "version": "1.0",
        "alias_length_violation_count": _ALIAS_LEN_VIOLATIONS,
        "alias_max_len": _ALIAS_MAX_LEN,
        "suggest_limit_min": SUGGEST_MIN_LIMIT,
        "suggest_limit_max": SUGGEST_MAX_LIMIT,
        "suggest_limit_default": SUGGEST_DEFAULT_LIMIT,
        "reconciliations_count": _RECON_RECONCILIATIONS_TOTAL,
        "recon_links_count": _RECON_LINKS_TOTAL,
        "config_ok": cfg.ok,
        "config_issue_count": len(cfg.issues),
    })


@bp.get("/api/conciliacion/healthz")
def healthz():
    return jsonify({"ok": True})


@bp.post("/api/conciliacion/suggest")
def suggest():
    global _ENG_SUCCESS, _ENG_FALLBACK, _ENG_ERROR, _ENG_EMPTY
    started = time.time()
    body = request.get_json(silent=True) or {}
    context_raw = (body.get("context") or "").strip().lower()
    source_type = (body.get("source_type") or "").strip().lower()
    context_value = context_raw or source_type
    valid_contexts = {"bank", "sales", "purchase", "expense", "payroll", "tax"}
    if context_value and context_value not in valid_contexts:
        return jsonify({"error": "invalid_context"}), 422
    limit = _sanitize_limit(_coerce_int(body.get("limit")))
    movement_id = _coerce_int(body.get("movement_id"))
    outcome = "fallback"
    results: List[Dict[str, Any]] = []
    try:
        if movement_id is not None:
            ctx = context_value or "bank"
            results = suggest_for_movement(ctx, movement_id, limit)
            outcome = "success" if results else "empty"
        elif context_value:
            outcome = "empty"
        else:
            return jsonify({"error": "movement_id requerido"}), 400
    except Exception:  # pragma: no cover
        outcome = "error"
        results = []
    finally:
        if not _metrics_disabled():
            _record_latency(time.time() - started)
            if outcome == "success":
                _ENG_SUCCESS += 1
            elif outcome == "fallback":
                _ENG_FALLBACK += 1
            elif outcome == "error":
                _ENG_ERROR += 1
            elif outcome == "empty":
                _ENG_EMPTY += 1
        # Emit structured log with current latency summary snapshot (cheap window read)
        if _structured_logging_enabled():
            comp = compute_latency_summary(list(_LATENCIES), _latency_buckets(), _slo_target())
            summary = comp["summary"]
            _emit_structured("recon_suggest_request", {
                "context": context_value or None,
                "movement_id": movement_id,
                "limit": limit,
                "outcome": outcome,
                "latency_seconds": round(time.time() - started, 6),
                "latency_window": summary,
                "slo_p95_target": _slo_target(),
                "slo_violations_total": _SLO_VIOLATIONS,
                "window_size": _LATENCIES.maxlen,
                "sample_count": summary["count"],
            })
    if context_value:
        return jsonify({"context": context_value, "items": results, "limit": limit, "outcome": outcome, "limit_used": limit, "limit_min": SUGGEST_MIN_LIMIT, "limit_max": SUGGEST_MAX_LIMIT, "limit_default": SUGGEST_DEFAULT_LIMIT})
    return jsonify({"movement_id": movement_id, "limit": limit, "outcome": outcome, "results": results})


bp.add_url_rule("/api/conciliacion/sugerencias", endpoint="sugerencias", view_func=suggest, methods=["POST"])  # type: ignore[arg-type]


@bp.post("/api/conciliacion/preview")
def preview():
    body = request.get_json(silent=True) or {}
    links_data = body.get("links")
    if not isinstance(links_data, list) or not links_data:
        return jsonify({"error": "invalid_payload"}), 422
    invoice_deltas: Dict[str, float] = {}
    movement_deltas: Dict[str, float] = {}
    for link in links_data:
        amt = link.get("amount")
        try:
            val = float(amt)
        except Exception:
            val = 0.0
        if link.get("sales_invoice_id") is not None:
            k = f"sales:{link['sales_invoice_id']}"
            invoice_deltas[k] = invoice_deltas.get(k, 0.0) + val
        if link.get("purchase_invoice_id") is not None:
            k = f"purchase:{link['purchase_invoice_id']}"
            invoice_deltas[k] = invoice_deltas.get(k, 0.0) + val
        if link.get("bank_movement_id") is not None:
            k = str(link["bank_movement_id"])
            movement_deltas[k] = movement_deltas.get(k, 0.0) + val
    return jsonify({"ok": True, "preview": {"invoice_deltas": invoice_deltas, "movement_deltas": movement_deltas}})


@bp.post("/api/conciliacion/confirmar")
def confirmar():
    body = request.get_json(silent=True) or {}
    # Backward compatible dual-mode behaviour:
    # 1) Modern simple path: expects movement_id -> insert into reconciliations table.
    # 2) Legacy alias path (existing tests): expects context/links/metadata with alias & canonical.
    #    We upsert into recon_aliases(alias unique) truncating to 120 chars just like legacy API.
    movement_id = _coerce_int(body.get("movement_id"))
    context = body.get("context")
    links_in = body.get("links") if isinstance(body.get("links"), list) else None
    meta = body.get("metadata") or {}
    alias_raw = (meta.get("alias") or "").strip()
    canonical_raw = (meta.get("canonical") or "").strip()
    confidence = meta.get("confidence") or body.get("confidence")
    try:
        confidence_val = float(confidence) if confidence is not None else None
    except Exception:  # pragma: no cover
        confidence_val = None

    # Ensure globals accessible for both paths
    global _RECON_RECONCILIATIONS_TOTAL, _RECON_LINKS_TOTAL, _ALIAS_LEN_VIOLATIONS

    # Path S: simple intention (source_ref / target_ref) -> accept w/out links
    source_ref = body.get("source_ref")
    target_ref = body.get("target_ref")
    if source_ref and target_ref and context and not links_in and movement_id is None:
        with db_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recon_reconciliations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context TEXT,
                    confidence REAL,
                    movement_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur = conn.execute(
                "INSERT INTO recon_reconciliations(context, confidence, movement_id) VALUES (?,?,?)",
                (str(context), confidence_val, None),
            )
            rid = cur.lastrowid
        _RECON_RECONCILIATIONS_TOTAL += 1
        if _structured_logging_enabled():
            _emit_structured("recon_confirmar_request", {
                "variant": "simple_intention",
                "context": context,
                "movement_id": None,
                "reconciliation_id": rid,
                "accepted": True,
                "confidence": confidence_val,
            })
        return jsonify({"ok": True, "accepted": True, "reconciliation_id": rid})

    # Path A: simplified modern path (movement_id only)
    if movement_id is not None and not links_in:
        with db_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recon_reconciliations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context TEXT,
                    confidence REAL,
                    movement_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur = conn.execute(
                "INSERT INTO recon_reconciliations(context, confidence, movement_id) VALUES (?,?,?)",
                ("movement", confidence_val, movement_id),
            )
            recon_id = cur.lastrowid
        _RECON_RECONCILIATIONS_TOTAL += 1
        if _structured_logging_enabled():
            _emit_structured("recon_confirmar_request", {
                "variant": "movement_only",
                "context": "movement",
                "movement_id": movement_id,
                "reconciliation_id": recon_id,
                "accepted": True,
                "confidence": confidence_val,
            })
        return jsonify({"ok": True, "reconciliation_id": recon_id})

    # Path B: legacy style with context + links (alias optional for backward compatibility)
    if context and links_in is not None:
        # Ensure tables exist (legacy compatibility) including aliases
        try:
            legacy_compat.bootstrap_tables(include_alias=True)
        except Exception:  # pragma: no cover
            pass
        # Normalize and truncate via legacy helper
        links_norm = legacy_compat.normalize_links(links_in)
        alias_t, truncated = legacy_compat.truncate_alias(alias_raw)
        canonical_t, _ = legacy_compat.truncate_alias(canonical_raw) if canonical_raw else (alias_t, False)
        if truncated:
            _ALIAS_LEN_VIOLATIONS += 1
        legacy_compat.bootstrap_tables(include_alias=bool(alias_t))
        recon_id = legacy_compat.insert_reconciliation(str(context), confidence_val)
        _RECON_RECONCILIATIONS_TOTAL += 1
        combined = legacy_compat.maybe_insert_combined_row(recon_id, links_norm)
        if not combined:
            _RECON_LINKS_TOTAL += legacy_compat.insert_links(recon_id, links_norm)
        else:
            # combined row counts as one; avoid double counting if we still want single-side rows omitted
            pass
        if alias_t:
            legacy_compat.upsert_alias(alias_t, canonical_t or alias_t)
        resp = {"ok": True, "reconciliation_id": recon_id}
        if alias_t:
            resp.update({"alias": alias_t, "canonical": canonical_t or alias_t, "alias_truncated": truncated, "alias_original_length": len(alias_raw)})
        if _structured_logging_enabled():
            _emit_structured("recon_confirmar_request", {
                "variant": "legacy_links",
                "context": context,
                "movement_id": movement_id,
                "reconciliation_id": recon_id,
                "links_count": len(links_norm),
                "alias_present": bool(alias_t),
                "alias_truncated": bool(truncated),
                "confidence": confidence_val,
            })
        return jsonify(resp)

    # Neither legacy nor modern path matched
    if context and movement_id is None and not links_in and not (source_ref and target_ref):
        return jsonify({"error": "invalid_payload"}), 422
    return jsonify({"error": "movement_id requerido"}), 422


@bp.get("/api/conciliacion/historial")
def historial():
    with db_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recon_reconciliations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                context TEXT,
                confidence REAL,
                movement_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        rows = conn.execute(
            "SELECT id, context, confidence, movement_id, created_at FROM recon_reconciliations ORDER BY id DESC LIMIT 100"
        ).fetchall()
        items = []
        for row in rows:
            data = dict(row)
            monto = conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM recon_links WHERE reconciliation_id=?",
                (row["id"],),
            ).fetchone()[0]
            data["monto"] = float(monto or 0.0)
            items.append(data)
    return jsonify({"items": items})


@bp.get("/api/conciliacion/links")
def links():
    args = request.args
    bank_id = _coerce_int(args.get("bank_id"))
    expense_id = _coerce_int(args.get("expense_id"))
    payroll_id = _coerce_int(args.get("payroll_id"))
    tax_id = _coerce_int(args.get("tax_id"))
    sales_doc = args.get("sales_doc")
    sales_date = args.get("sales_date")
    purchase_doc = args.get("purchase_doc")
    purchase_date = args.get("purchase_date")
    payroll_period = args.get("payroll_period")
    payroll_rut = args.get("payroll_rut")
    tax_period = args.get("tax_period")
    tax_tipo = args.get("tax_tipo")
    with db_conn() as conn:
        cur = conn.cursor()
        # Early return if no params
        if not any([
            bank_id, expense_id, payroll_id, tax_id, sales_doc, purchase_doc,
            payroll_period and payroll_rut, tax_period and tax_tipo
        ]):
            return jsonify({"items": []})
        # Resolve invoice ids when docs provided
        sales_invoice_id = None
        purchase_invoice_id = None
        if sales_doc and sales_date:
            row = cur.execute(
                "SELECT id FROM sales_invoices WHERE invoice_number=? AND invoice_date=?",
                (sales_doc, sales_date),
            ).fetchone()
            if row:
                sales_invoice_id = row[0]
        if purchase_doc and purchase_date:
            row = cur.execute(
                "SELECT id FROM ap_invoices WHERE invoice_number=? AND invoice_date=?",
                (purchase_doc, purchase_date),
            ).fetchone()
            if row:
                purchase_invoice_id = row[0]
        if payroll_period and payroll_rut and payroll_id is None:
            row = cur.execute(
                "SELECT id FROM payroll_slips WHERE periodo=? AND rut_trabajador=?",
                (payroll_period, payroll_rut),
            ).fetchone()
            if row:
                payroll_id = row[0]
        if tax_period and tax_tipo and tax_id is None:
            row = cur.execute(
                "SELECT id FROM taxes WHERE periodo=? AND tipo=?",
                (tax_period, tax_tipo),
            ).fetchone()
            if row:
                tax_id = row[0]
        # Build where clause
        clauses = []
        params: List[Any] = []
        if bank_id:
            clauses.append("bank_movement_id=?")
            params.append(bank_id)
        if sales_invoice_id:
            clauses.append("sales_invoice_id=?")
            params.append(sales_invoice_id)
        if purchase_invoice_id:
            clauses.append("purchase_invoice_id=?")
            params.append(purchase_invoice_id)
        if expense_id:
            clauses.append("expense_id=?")
            params.append(expense_id)
        if payroll_id:
            clauses.append("payroll_id=?")
            params.append(payroll_id)
        if tax_id:
            clauses.append("tax_id=?")
            params.append(tax_id)
        if not clauses:
            return jsonify({"items": []})
        where_sql = " OR ".join(clauses)
        rows = cur.execute(
            f"SELECT id, reconciliation_id, bank_movement_id, sales_invoice_id, purchase_invoice_id, expense_id, payroll_id, tax_id, amount FROM recon_links WHERE {where_sql}",
            params,
        ).fetchall()
        out = []
        for r in rows:
            bank_movement_id = r[2]
            sales_id = r[3]
            purchase_id = r[4]
            expense_id_r = r[5]
            payroll_id_r = r[6]
            tax_id_r = r[7]
            # Determine perspective
            if bank_id and sales_id:
                doc = cur.execute("SELECT invoice_number FROM sales_invoices WHERE id=?", (sales_id,)).fetchone()
                if doc:
                    out.append({"type": "sales", "ref": doc[0]})
                else:  # fallback when sales invoice row not present (test minimal scenario)
                    out.append({"type": "sales", "ref": f"sales:{sales_id}"})
                continue
            if sales_invoice_id and bank_movement_id:
                bm = cur.execute("SELECT referencia FROM bank_movements WHERE id=?", (bank_movement_id,)).fetchone()
                if bm:
                    out.append({"type": "bank", "ref": bm[0]})
                else:
                    out.append({"type": "bank", "ref": f"bm:{bank_movement_id}"})
                continue
            if purchase_id and sales_id:
                doc = cur.execute("SELECT invoice_number FROM sales_invoices WHERE id=?", (sales_id,)).fetchone()
                if doc:
                    out.append({"type": "sales", "ref": doc[0]})
                else:
                    out.append({"type": "sales", "ref": f"sales:{sales_id}"})
                continue
            if purchase_id:
                doc = cur.execute("SELECT invoice_number FROM ap_invoices WHERE id=?", (purchase_id,)).fetchone()
                if doc:
                    out.append({"type": "purchase", "ref": doc[0]})
                else:
                    out.append({"type": "purchase", "ref": f"purchase:{purchase_id}"})
                continue
            if sales_id:
                doc = cur.execute("SELECT invoice_number FROM sales_invoices WHERE id=?", (sales_id,)).fetchone()
                if doc:
                    out.append({"type": "sales", "ref": doc[0]})
                else:
                    out.append({"type": "sales", "ref": f"sales:{sales_id}"})
                continue
            if expense_id_r:
                ex = cur.execute("SELECT descripcion FROM expenses WHERE id=?", (expense_id_r,)).fetchone()
                if ex:
                    out.append({"type": "expense", "ref": ex[0]})
                    continue
            if payroll_id_r:
                py = cur.execute("SELECT periodo FROM payroll_slips WHERE id=?", (payroll_id_r,)).fetchone()
                if py:
                    out.append({"type": "payroll", "ref": py[0]})
                    continue
            if tax_id_r:
                tx = cur.execute("SELECT tipo FROM taxes WHERE id=?", (tax_id_r,)).fetchone()
                if tx:
                    out.append({"type": "tax", "ref": tx[0]})
                    continue
        return jsonify({"items": out})


@bp.get("/api/conciliacion/metrics")
def metrics_text():
    if _metrics_disabled():
        return jsonify({"error": "metrics disabled"}), 404
    payload = _metrics_payload()
    base = _prom_text(payload)
    # Append legacy compatibility metrics expected by older tests
    legacy_lines = [
        "recon_engine_available 1",  # simple availability gauges
        "recon_adapter_available 1",
        f"recon_reconciliations_total {_RECON_RECONCILIATIONS_TOTAL}",
        f"recon_links_total {_RECON_LINKS_TOTAL}",
        f"recon_alias_max_len {_ALIAS_MAX_LEN}",
        f"recon_suggest_limit_min {SUGGEST_MIN_LIMIT}",
        f"recon_suggest_limit_max {SUGGEST_MAX_LIMIT}",
        f"recon_suggest_limit_default {SUGGEST_DEFAULT_LIMIT}",
        f"recon_alias_length_violation_count {_ALIAS_LEN_VIOLATIONS}",
    ]
    text = base + "\n".join(legacy_lines) + "\n"
    return current_app.response_class(text, mimetype="text/plain; version=0.0.4")


@bp.get("/api/conciliacion/metrics/prom")
def metrics_prom():
    if not _prom_client_enabled():
        return jsonify({"error": "prometheus_client disabled"}), 404
    try:
        # Added Histogram + more gauges for ratios and totals
        from prometheus_client import (
            CollectorRegistry,
            Gauge,
            Counter,
            Histogram,
            generate_latest,
            CONTENT_TYPE_LATEST,
        )  # type: ignore
    except Exception:  # pragma: no cover
        return jsonify({"error": "prometheus_client not installed"}), 500
    reg = CollectorRegistry()
    payload = _metrics_payload()
    s = payload["suggest_latency"]
    # Basic latency summary gauges
    Gauge("recon_suggest_latency_avg_seconds", "Average latency", registry=reg).set(s["avg"])
    Gauge("recon_suggest_latency_p50_seconds", "P50 latency", registry=reg).set(s["p50"])
    Gauge("recon_suggest_latency_p95_seconds", "P95 latency", registry=reg).set(s["p95"])
    Gauge("recon_suggest_latency_p99_seconds", "P99 latency", registry=reg).set(s["p99"])
    Gauge("recon_suggest_latency_count", "Sample count (window)", registry=reg).set(s["count"])
    Gauge("recon_suggest_latency_sum_seconds", "Sum of latencies in window", registry=reg).set(s["sum"])

    # Histogram reconstructed on-demand from current window (does not accumulate across restarts)
    try:
        buckets = _latency_buckets()
        # Ensure buckets strictly increasing & positive
        buckets = [b for b in buckets if b > 0]
        if buckets:
            h = Histogram(
                "recon_suggest_latency_seconds",
                "Suggest latency (window histogram)",
                buckets=buckets,
                registry=reg,
            )
            for v in list(_LATENCIES):  # observe current samples
                h.observe(v)
    except Exception:  # pragma: no cover
        pass

    c_slo = Counter("recon_suggest_slo_p95_violation_total", "SLO p95 violations", registry=reg)
    if _SLO_VIOLATIONS:
        c_slo._value.set(_SLO_VIOLATIONS)  # type: ignore[attr-defined]
    eng = payload["engine"]
    total_requests = (
        eng["success_total"]
        + eng["fallback_total"]
        + eng["error_total"]
        + eng["empty_total"]
    )
    Gauge("recon_engine_requests_total", "Total engine requests (sum of outcomes)", registry=reg).set(total_requests)
    # Outcome totals as counters (window-based, non-monotonic across restarts)
    for k in ["success_total", "fallback_total", "error_total", "empty_total"]:
        ctr = Gauge(f"recon_engine_{k}", f"Engine {k} (window total)", registry=reg)
        ctr.set(eng[k])
    # Ratios (instantaneous gauges)
    for k in ["success_ratio", "fallback_ratio", "error_ratio", "empty_ratio"]:
        Gauge(f"recon_engine_{k}", f"Engine {k} (ratio of window total)", registry=reg).set(eng[k])

    persist = payload["persist"]
    Gauge("recon_persist_pending_samples", "Pending latencies awaiting flush", registry=reg).set(persist["pending"])
    Gauge("recon_persist_flush_total", "Number of persistence flushes", registry=reg).set(persist["flushes"])
    last_flush = float(persist.get("last_flush_at") or 0.0)
    age = max(0.0, time.time() - last_flush) if last_flush else 0.0
    Gauge("recon_persist_last_flush_age_seconds", "Seconds since last flush (0 if never)", registry=reg).set(age)
    Gauge("recon_persist_force_compress", "Force gzip compression flag (1/0)", registry=reg).set(1 if persist["force_compress"] else 0)
    Gauge("recon_persist_compress_min_bytes", "Minimum payload bytes to trigger compression", registry=reg).set(persist["compress_min_bytes"])
    Gauge("recon_persist_last_size_bytes", "Size in bytes of last persisted file (compressed or plain)", registry=reg).set(persist["last_size_bytes"])
    Gauge("recon_persist_last_raw_bytes", "Uncompressed size (bytes) of last payload", registry=reg).set(persist["last_raw_bytes"])
    Gauge("recon_persist_last_compression_ratio", "Compression ratio (compressed/raw)", registry=reg).set(persist["compression_ratio"])
    Gauge("recon_persist_error_total", "Total persistence write errors", registry=reg).set(persist["errors"])

    # Utilization / RPS style gauges
    Gauge("recon_requests_per_second_60s", "Requests per second (approx) over last 60s", registry=reg).set(
        payload["requests_per_second_60s"]
    )
    Gauge("recon_requests_per_second_300s", "Requests per second (approx) over last 300s", registry=reg).set(
        payload["requests_per_second_300s"]
    )
    Gauge("recon_window_size", "Max latency window size", registry=reg).set(payload["window_size"])
    Gauge("recon_latency_window_filled", "Current number of stored latencies", registry=reg).set(s["count"])
    Gauge("recon_slo_p95_target_seconds", "Configured p95 SLO target", registry=reg).set(payload["slo_p95_target"])
    # Structured logging counters
    sl = payload.get("structured_logging", {})
    Gauge("recon_structured_logging_enabled", "Structured logging enabled flag", registry=reg).set(1 if sl.get("enabled") else 0)
    Gauge("recon_structured_logging_emitted_total", "Total structured events emitted (process lifetime)", registry=reg).set(sl.get("emitted_total", 0))
    Gauge("recon_structured_logging_sampled_out_total", "Structured events skipped by sampling", registry=reg).set(sl.get("sampled_out_total", 0))
    Gauge("recon_structured_logging_schema_version", "Structured log schema version", registry=reg).set(sl.get("schema_version", SCHEMA_VERSION))
    Gauge("recon_structured_logging_emit_failures_total", "Structured logging primary emission failures", registry=reg).set(sl.get("emit_failures_total", 0))
    # Async / extended structured logging gauges (added later for richer observability)
    if sl:
        Gauge("recon_structured_logging_async_enabled", "Structured logging async mode enabled flag", registry=reg).set(1 if sl.get("async_enabled") else 0)
        Gauge("recon_structured_logging_queue_dropped_total", "Structured logging events dropped due to full async queue", registry=reg).set(sl.get("queue_dropped_total", 0))
        Gauge("recon_structured_logging_async_queue_current", "Current async structured log queue size", registry=reg).set(sl.get("async_queue_current", 0))
        Gauge("recon_structured_logging_async_queue_max", "Max async structured log queue size", registry=reg).set(sl.get("async_queue_max", 0))
        # Utilization ratio gauge (0-1)
        Gauge("recon_structured_logging_async_queue_utilization", "Async structured log queue utilization (current/max)", registry=reg).set(sl.get("async_queue_utilization", 0.0))
        Gauge("recon_structured_logging_drop_ratio", "Structured logging async drop ratio (dropped/(emitted+dropped))", registry=reg).set(sl.get("drop_ratio", 0.0))
        Gauge("recon_structured_logging_overrides_active_count", "Count of active runtime overrides", registry=reg).set(sl.get("overrides_active_count", 0))
        # Failure ratio is instantaneous; keep as gauge (0-1)
        fr = sl.get("failure_ratio")
        try:
            fr_val = float(fr) if fr is not None else 0.0
        except Exception:  # pragma: no cover
            fr_val = 0.0
        Gauge("recon_structured_logging_failure_ratio", "Structured logging emission failure ratio (failures/emitted)", registry=reg).set(fr_val)
        # Age of last event gives staleness signal; -1 if never
        last_age = None
        last_ts = _LAST_STRUCTURED_EVENT_TS or None
        if last_ts:
            last_age = max(0.0, time.time() - last_ts)
        Gauge("recon_structured_logging_last_event_age_seconds", "Seconds since last structured log event (-1 if none)", registry=reg).set(last_age if last_age is not None else -1)
    body = generate_latest(reg)
    return current_app.response_class(body, mimetype=CONTENT_TYPE_LATEST)


@bp.post("/api/conciliacion/metrics/reset")
def metrics_reset():
    if _metrics_disabled():
        return jsonify({"error": "metrics disabled"}), 404
    token = os.environ.get("RECON_METRICS_RESET_TOKEN")
    provided = (
        request.headers.get("X-Reset-Token")
        or request.headers.get("X-Admin-Token")  # legacy header name in tests
        or request.args.get("token")
        or (request.get_json(silent=True) or {}).get("token")
    )
    if token and provided != token:
        return jsonify({"error": "unauthorized"}), 403
    global _SLO_VIOLATIONS, _ENG_SUCCESS, _ENG_FALLBACK, _ENG_ERROR, _ENG_EMPTY
    global _PERSIST_LAST, _PERSIST_PENDING, _PERSIST_LAST_SIZE, _PERSIST_LAST_RAW_SIZE, _PERSIST_ERRORS
    global _RESET_TS, _LAST_SAMPLE_VIOLATION, _SUGGEST_SLO_VIOLATION_TOTAL, _SUGGEST_LAT_LAST_RESET, _SUGGEST_LATENCIES
    with _LOCK:
        before = len(_LATENCIES)
        slo_before = _SLO_VIOLATIONS
        _LATENCIES.clear()
        _REQ_TS.clear()
        _RESET_TS = time.time()
        _SUGGEST_LAT_LAST_RESET = _RESET_TS
        _SLO_VIOLATIONS = 0
        _SUGGEST_SLO_VIOLATION_TOTAL = 0
        _ENG_SUCCESS = _ENG_FALLBACK = _ENG_ERROR = _ENG_EMPTY = 0
        _LAST_SAMPLE_VIOLATION = 0
        _PERSIST_LAST = 0.0
        _PERSIST_PENDING = 0
        _PERSIST_LAST_SIZE = 0
        _PERSIST_LAST_RAW_SIZE = 0
        _PERSIST_ERRORS = 0
    _persist(force=True)
    payload = {
        "ok": True,
        "reset_at": _RESET_TS,
        "before": before,
        "after": len(_LATENCIES),
        "slo_violation_total_before": slo_before,
        "slo_violation_total_after": 0,
        "buckets": _latency_buckets(),
    }
    if _structured_logging_enabled():
        _emit_structured("recon_metrics_reset", payload)
    return jsonify(payload)


def _test_mode_enabled() -> bool:
    # Also treat presence of PYTEST_CURRENT_TEST as test mode to avoid brittle env requirements
    return (
        _e_bool("RECON_TEST_MODE")
        or os.environ.get("FLASK_ENV") == "test"
        or "PYTEST_CURRENT_TEST" in os.environ
    )


def test_reset_internal() -> None:  # helper para tests sin token
    if not _test_mode_enabled():
        raise RuntimeError("test reset only available in test mode")
    # Replicate core of metrics_reset without requiring a Flask request context
    if _metrics_disabled():  # if metrics disabled simply no-op for internal call
        return
    global _SLO_VIOLATIONS, _ENG_SUCCESS, _ENG_FALLBACK, _ENG_ERROR, _ENG_EMPTY
    global _PERSIST_LAST, _PERSIST_PENDING, _PERSIST_LAST_SIZE, _PERSIST_LAST_RAW_SIZE, _PERSIST_ERRORS
    global _RESET_TS, _LAST_SAMPLE_VIOLATION, _SUGGEST_SLO_VIOLATION_TOTAL, _SUGGEST_LAT_LAST_RESET, _SUGGEST_LATENCIES
    with _LOCK:
        _LATENCIES.clear()
        _REQ_TS.clear()
        _RESET_TS = time.time()
        _SUGGEST_LAT_LAST_RESET = _RESET_TS
        _SLO_VIOLATIONS = 0
        _SUGGEST_SLO_VIOLATION_TOTAL = 0
        _ENG_SUCCESS = _ENG_FALLBACK = _ENG_ERROR = _ENG_EMPTY = 0
        _LAST_SAMPLE_VIOLATION = 0
        _PERSIST_LAST = 0.0
        _PERSIST_PENDING = 0
        _PERSIST_LAST_SIZE = 0
        _PERSIST_LAST_RAW_SIZE = 0
        _PERSIST_ERRORS = 0
        if _SUGGEST_LATENCIES is not _LATENCIES:
            try:
                _SUGGEST_LATENCIES.clear()
            except Exception:  # pragma: no cover
                pass
    _persist(force=True)

# Debug helpers


def _debug_auth() -> bool:
    if not _e_bool("RECON_METRICS_DEBUG"):
        return False  # treated as 404
    token = os.environ.get("RECON_METRICS_DEBUG_TOKEN")
    if not token:
        return True
    provided = (
        request.headers.get("X-Debug-Token")
        or request.headers.get("X-Admin-Token")
        or request.args.get("token")
    )
    if provided == token:
        return True
    # Mark a flag so route can return 403 instead of 404
    request._recon_forbidden = True  # type: ignore[attr-defined]
    return False


@bp.get("/api/conciliacion/metrics/latencies")
def metrics_latencies():
    if not _debug_auth():
        status_code = 403 if getattr(request, "_recon_forbidden", False) else 404
        return jsonify({"error": "debug disabled"}), status_code
    limit_raw = request.args.get("limit")
    lst = list(_LATENCIES)
    if limit_raw:
        try:
            lim = int(limit_raw)
            if lim >= 0:
                lst = lst[-lim:]
        except Exception:  # pragma: no cover
            pass
    return jsonify({"latencies": lst, "count": len(lst)})


@bp.get("/api/conciliacion/metrics/json")
def metrics_json():
    if not _debug_auth():
        status_code = 403 if getattr(request, "_recon_forbidden", False) else 404
        return jsonify({"error": "debug disabled"}), status_code
    return jsonify(_metrics_payload())


@bp.get("/api/conciliacion/logs/schema")
def logs_schema():
    """Expose structured logging schema metadata for tooling & validation.

    Always available when structured logging is enabled; otherwise 404 to avoid
    implying logging surface when feature disabled.
    """
    if not _structured_logging_enabled():
        return jsonify({"error": "structured_logging_disabled"}), 404
    core = sorted(list(_REDACT_CORE))
    return jsonify({
        "schema_version": SCHEMA_VERSION,
        "core_fields": core,
        "events": _EVENT_SCHEMA,
        "redaction_env": "RECON_STRUCTURED_REDACT",
        "debug_flags_env": "RECON_DEBUG_FLAGS",
    })


@bp.get("/api/conciliacion/logs/config")
def logs_config():
    """Runtime configuration & counters for structured logs.

    Provides introspection for operators & tests. Always 404 if feature disabled
    to avoid signaling accidental exposure.
    """
    if not _structured_logging_enabled():
        return jsonify({"error": "structured_logging_disabled"}), 404

    # Collect per-event overrides actually set (not just theoretical)
    overrides: Dict[str, float] = {}
    prefix = "RECON_STRUCTURED_LOG_SAMPLE_"
    for k, v in os.environ.items():
        if not k.startswith(prefix):
            continue
        # Skip the base global variable if misnamed
        if k == "RECON_STRUCTURED_LOG_SAMPLE_":
            continue
        try:
            rate = float(v)
        except Exception:
            continue
        if 0.0 <= rate <= 1.0:
            # derive logical event token (reverse of transformation best-effort)
            event_token = k[len(prefix):]
            overrides[event_token] = rate

    global_rate = os.environ.get("RECON_STRUCTURED_LOG_SAMPLE")
    try:
        gr = float(global_rate) if global_rate is not None else 1.0
        if not (0.0 <= gr <= 1.0):
            gr = 1.0
    except Exception:
        gr = 1.0

    redaction = sorted(list(_redact_fields()))
    dbg = _debug_flags()
    payload = {
        "enabled": True,
        "schema_version": SCHEMA_VERSION,
        "global_sample_rate": gr,
        "per_event_sample_overrides": overrides,
        "runtime_overrides": {
            k: v for k, v in _RUNTIME_OVERRIDES.items() if k in {"global_sample_rate", "per_event_sample", "structured_logs_enabled", "async_enabled"}
        },
        "redacted_fields": redaction,
        "debug_flags": dbg,
        "counters": {
            "emitted_total": _EMITTED_EVENTS_TOTAL,
            "sampled_out_total": _SAMPLED_OUT_EVENTS_TOTAL,
            "emit_failures_total": _EMIT_FAILURES_TOTAL,
            "queue_dropped_total": _ASYNC_DROPPED,
            "async_queue_current": (_ASYNC_QUEUE.qsize() if _ASYNC_QUEUE is not None else 0),
            "async_queue_max": (_ASYNC_QUEUE.maxsize if _ASYNC_QUEUE is not None else 0),
            "async_queue_utilization": (
                (_ASYNC_QUEUE.qsize() / _ASYNC_QUEUE.maxsize) if (_ASYNC_QUEUE is not None and _ASYNC_QUEUE.maxsize) else 0.0
            ),
            "drop_ratio": ((_ASYNC_DROPPED / (_EMITTED_EVENTS_TOTAL + _ASYNC_DROPPED)) if (_EMITTED_EVENTS_TOTAL + _ASYNC_DROPPED) else 0.0),
            "overrides_active_count": sum(1 for k in _RUNTIME_OVERRIDES.keys() if k in {"global_sample_rate", "per_event_sample", "structured_logs_enabled", "async_enabled"}),
            "failure_ratio": (_EMIT_FAILURES_TOTAL / _EMITTED_EVENTS_TOTAL) if _EMITTED_EVENTS_TOTAL else 0.0,
        },
        "env_keys": {
            "global_sample": "RECON_STRUCTURED_LOG_SAMPLE",
            "per_event_prefix": prefix,
            "redact": "RECON_STRUCTURED_REDACT",
            "debug_flags": "RECON_DEBUG_FLAGS",
            "async_enabled": "RECON_STRUCTURED_LOG_ASYNC",
            "async_queue_size": "RECON_STRUCTURED_LOG_ASYNC_QUEUE",
        },
    }
    return jsonify(payload)


@bp.post("/api/conciliacion/logs/runtime")
def logs_runtime_update():
    """Mutate in-memory structured logging runtime overrides.

    Body JSON fields (all optional):
      global_sample_rate: float in [0,1]
      per_event_sample: { EVENT_TOKEN: float }
      structured_logs_enabled: bool
      async_enabled: bool

    Security: gated by header X-Runtime-Token if RECON_RUNTIME_UPDATE_TOKEN env set.
    Returns current effective overrides after mutation. Does NOT persist to disk.
    404 if structured logging feature base is not enabled (cannot bootstrap runtime otherwise).
    """
    if not _structured_logging_enabled():
        return jsonify({"error": "structured_logging_disabled"}), 404
    token_env = os.environ.get("RECON_RUNTIME_UPDATE_TOKEN")
    if token_env:
        provided = (
            request.headers.get("X-Runtime-Token")
            or request.headers.get("X-Admin-Token")
            or (request.get_json(silent=True) or {}).get("token")
        )
        if provided != token_env:
            return jsonify({"error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    changed: Dict[str, Any] = {}
    # Global sample rate
    if "global_sample_rate" in body:
        val = body.get("global_sample_rate")
        try:
            if val is None:
                raise ValueError("missing")
            f = float(val)
            if 0.0 <= f <= 1.0:
                _RUNTIME_OVERRIDES["global_sample_rate"] = f
                changed["global_sample_rate"] = f
            else:
                return jsonify({"error": "invalid_global_sample_rate"}), 400
        except Exception:
            return jsonify({"error": "invalid_global_sample_rate"}), 400
    # Structured logs enabled toggle
    if "structured_logs_enabled" in body:
        _RUNTIME_OVERRIDES["structured_logs_enabled"] = bool(body.get("structured_logs_enabled"))
        changed["structured_logs_enabled"] = _RUNTIME_OVERRIDES["structured_logs_enabled"]
    # Async enabled toggle
    if "async_enabled" in body:
        _RUNTIME_OVERRIDES["async_enabled"] = bool(body.get("async_enabled"))
        changed["async_enabled"] = _RUNTIME_OVERRIDES["async_enabled"]
    # Per-event sample overrides map
    if "per_event_sample" in body:
        m = body.get("per_event_sample") or {}
        if not isinstance(m, dict):
            return jsonify({"error": "invalid_per_event_sample"}), 400
        cleaned: Dict[str, float] = {}
        for k, v in m.items():
            token = re.sub(r"[^A-Za-z0-9]", "_", str(k)).upper()
            try:
                f = float(v)
            except Exception:
                return jsonify({"error": f"invalid_rate_for_{k}"}), 400
            if not (0.0 <= f <= 1.0):
                return jsonify({"error": f"invalid_rate_for_{k}"}), 400
            cleaned[token] = f
        _RUNTIME_OVERRIDES["per_event_sample"] = cleaned
        changed["per_event_sample"] = cleaned
    # If async newly enabled ensure worker
    if _RUNTIME_OVERRIDES.get("async_enabled"):
        _ensure_async_worker()
    return jsonify({
        "ok": True,
        "changed": changed,
        "effective_overrides": {
            k: v for k, v in _RUNTIME_OVERRIDES.items() if k in {"global_sample_rate", "per_event_sample", "structured_logs_enabled", "async_enabled"}
        }
    })


@bp.delete("/api/conciliacion/logs/runtime")
def logs_runtime_reset():
    """Clear all runtime overrides, returning previous effective set.

    Security: same token gating as POST. 404 if structured logging base disabled.
    """
    if not _structured_logging_enabled():
        return jsonify({"error": "structured_logging_disabled"}), 404
    token_env = os.environ.get("RECON_RUNTIME_UPDATE_TOKEN")
    if token_env:
        provided = (
            request.headers.get("X-Runtime-Token")
            or request.headers.get("X-Admin-Token")
            or (request.get_json(silent=True) or {}).get("token")
        )
        if provided != token_env:
            return jsonify({"error": "unauthorized"}), 403
    prev = {k: v for k, v in _RUNTIME_OVERRIDES.items()}
    _RUNTIME_OVERRIDES.clear()
    return jsonify({"ok": True, "cleared": True, "previous_overrides": prev})


@bp.get("/api/conciliacion/logs/health")
def logs_health():
    """Lightweight health/introspection for structured logging runtime.

    Includes failure ratio and staleness of last event. 404 if feature disabled.
        #
    """
    if not _structured_logging_enabled():
        return jsonify({"error": "structured_logging_disabled"}), 404
    now = time.time()
    emitted = _EMITTED_EVENTS_TOTAL
    failures = _EMIT_FAILURES_TOTAL
    failure_ratio = (failures / emitted) if emitted else 0.0
    last_ts = _LAST_STRUCTURED_EVENT_TS or None
    age = (now - last_ts) if last_ts else None
    return jsonify({
        "enabled": True,
        "schema_version": SCHEMA_VERSION,
        "emitted_total": emitted,
        "emit_failures_total": failures,
        "sampled_out_total": _SAMPLED_OUT_EVENTS_TOTAL,
        "failure_ratio": failure_ratio,
        "last_event_timestamp": last_ts,
        "last_event_age_seconds": age,
        "async_enabled": _async_logging_enabled(),
        "queue_dropped_total": _ASYNC_DROPPED,
    })


@bp.get("/api/conciliacion/metrics/latencies/snapshot")
def metrics_snapshot_get():
    if not _debug_auth():
        status_code = 403 if getattr(request, "_recon_forbidden", False) else 404
        return jsonify({"error": "debug disabled"}), status_code
    path = _persist_path()
    if not path:
        return jsonify({"error": "persistence disabled"}), 400
    # Try file snapshot first
    for candidate in (path, path + '.gz'):
        p = Path(candidate)
        if p.exists():
            try:
                if candidate.endswith('.gz'):
                    with gzip.open(p, 'rt', encoding='utf-8') as fh:  # type: ignore[arg-type]
                        data = json.load(fh)
                else:
                    data = json.loads(p.read_text(encoding='utf-8'))
                # Normalize to legacy expected payload shape
                lat = []
                version = 1
                if isinstance(data, dict):
                    lat = data.get('latencies') or []
                elif isinstance(data, list):
                    lat = data
                return jsonify({"latencies": lat, "version": version, "source": "file"})
            except Exception as exc:  # pragma: no cover
                return jsonify({"error": str(exc)}), 500
    # Fallback to live window
    return jsonify({"latencies": list(_LATENCIES), "version": 1, "source": "live"})


@bp.delete("/api/conciliacion/metrics/latencies/snapshot")
def metrics_snapshot_delete():
    if not _debug_auth():
        status_code = 403 if getattr(request, "_recon_forbidden", False) else 404
        return jsonify({"error": "debug disabled"}), status_code
    path = _persist_path()
    if not path:
        return jsonify({"error": "persistence disabled"}), 400
    removed_any = False
    for candidate in (path, path + '.gz'):
        p = Path(candidate)
        if p.exists():
            try:
                p.unlink()
                removed_any = True
            except Exception:  # pragma: no cover
                pass
    cleared = False
    if request.args.get('clear') in {'1', 'true', 'yes'}:
        before = len(_LATENCIES)
        _LATENCIES.clear()
        cleared = before > 0
    return jsonify({"removed": removed_any, "cleared_memory": cleared})


# One-time load
_load_persisted()

__all__ = ["bp"]
