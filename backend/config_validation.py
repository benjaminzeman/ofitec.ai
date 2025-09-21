"""Startup configuration validation for reconciliation service.

Performs lightweight, non-invasive checks of environment variables and returns
structured results without raising hard failures (production should continue
with safe defaults). Designed so tests can also introspect validation output.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import os
import json
from typing import List, Dict, Any
from pathlib import Path


@dataclass
class ConfigIssue:
    key: str
    level: str  # warn|error|info
    message: str


@dataclass
class ConfigValidationResult:
    ok: bool
    issues: List[ConfigIssue]
    derived: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:  # JSON safe
        return {
            "ok": self.ok,
            "issues": [asdict(i) for i in self.issues],
            "derived": self.derived,
        }


_CACHED: ConfigValidationResult | None = None


def _parse_float_list(raw: str) -> List[float]:
    out: List[float] = []
    for p in raw.split(','):
        p = p.strip()
        if not p:
            continue
        try:
            v = float(p)
        except ValueError:
            continue
        if v > 0:
            out.append(v)
    return out


def validate_environment() -> ConfigValidationResult:
    global _CACHED
    if _CACHED is not None:
        return _CACHED
    issues: List[ConfigIssue] = []
    derived: Dict[str, Any] = {}
    env = os.environ

    # Buckets
    raw_buckets = env.get("RECON_LATENCY_BUCKETS", "")
    if raw_buckets:
        buckets = _parse_float_list(raw_buckets)
        if not buckets:
            issues.append(ConfigIssue("RECON_LATENCY_BUCKETS", "warn", "ignored: no valid positive floats"))
        else:
            if buckets != sorted(buckets):
                issues.append(ConfigIssue("RECON_LATENCY_BUCKETS", "warn", "not strictly increasing; will be sorted"))
            derived["bucket_count"] = len(buckets)
    # SLO target
    slo_raw = env.get("RECON_LATENCY_SLO_P95")
    if slo_raw:
        try:
            slo_v = float(slo_raw)
            if slo_v < 0:
                issues.append(ConfigIssue("RECON_LATENCY_SLO_P95", "warn", "negative -> treated as disabled"))
        except ValueError:
            issues.append(ConfigIssue("RECON_LATENCY_SLO_P95", "warn", "non-numeric -> ignored"))
    # Persistence path
    persist_path = env.get("RECON_LATENCY_PERSIST_PATH")
    if persist_path:
        p = Path(persist_path)
        parent = p.parent
        if not parent.exists():
            issues.append(ConfigIssue("RECON_LATENCY_PERSIST_PATH", "warn", f"directory {parent} does not exist"))
        else:
            if not os.access(parent, os.W_OK):
                issues.append(ConfigIssue("RECON_LATENCY_PERSIST_PATH", "error", f"directory {parent} not writable"))
    # Metrics disable dual vars
    if env.get("RECON_DISABLE_METRICS") and env.get("RECON_METRICS_DISABLED"):
        issues.append(ConfigIssue("metrics_disable_flags", "info", "both disable flags set; legacy precedence applies"))
    # Compression thresholds
    min_bytes = env.get("RECON_LATENCY_PERSIST_COMPRESS_MIN_BYTES")
    if min_bytes:
        try:
            v = int(min_bytes)
            if v < 512:
                issues.append(ConfigIssue("RECON_LATENCY_PERSIST_COMPRESS_MIN_BYTES", "info", "very low threshold may waste CPU"))
        except ValueError:
            issues.append(ConfigIssue("RECON_LATENCY_PERSIST_COMPRESS_MIN_BYTES", "warn", "non-integer -> default used"))
    # Window size
    win_raw = env.get("RECON_LATENCY_WINDOW_SIZE")
    if win_raw:
        try:
            w = int(win_raw)
            if w < 50:
                issues.append(ConfigIssue("RECON_LATENCY_WINDOW_SIZE", "warn", "too small; clamped to >=50"))
            elif w > 20000:
                issues.append(ConfigIssue("RECON_LATENCY_WINDOW_SIZE", "warn", "very large window may increase memory usage"))
        except ValueError:
            issues.append(ConfigIssue("RECON_LATENCY_WINDOW_SIZE", "warn", "non-integer -> default used"))

    ok = not any(i.level == "error" for i in issues)
    _CACHED = ConfigValidationResult(ok=ok, issues=issues, derived=derived)
    return _CACHED


def validation_summary_json() -> str:
    return json.dumps(validate_environment().to_dict(), separators=(",", ":"))
