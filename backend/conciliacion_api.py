"""Minimal legacy shim.

This file intentionally only re-exports the clean reconciliation blueprint.
If any additional code appears below the sentinel, remove it.
"""
from __future__ import annotations

from .conciliacion_api_clean import (  # type: ignore F401
    bp,
    suggest_for_movement,
    _SUGGEST_LATENCIES,
    _SUGGEST_SLO_VIOLATION_TOTAL,
    _SUGGEST_LAT_LAST_RESET,
)

# Wrapper para mantener nombre legacy _load_persisted apuntando siempre
# a la implementación actual del módulo clean tras reloads.
def _load_persisted():  # type: ignore
    """Legacy loader compatible con tests antiguos.

    Lee el archivo en RECON_LATENCY_PERSIST_PATH (o .gz) y pobla
    el deque alias _SUGGEST_LATENCIES filtrando valores no numéricos.
    También actualiza contadores de violaciones y last_reset si presentes.
    Ignora silenciosamente errores/corrupción manteniendo ventana vacía.
    """
    import os
    import json
    import gzip
    from pathlib import Path
    path = os.environ.get('RECON_LATENCY_PERSIST_PATH')
    if not path:
        return None
    candidates = (path, path + '.gz') if not path.endswith('.gz') else (path,)
    for candidate in candidates:
        p = Path(candidate)
        if not p.exists():
            continue
        try:
            if p.stat().st_size == 0:
                try:
                    p.unlink()
                except Exception:  # noqa: BLE001
                    pass
                continue
            if candidate.endswith('.gz'):
                with gzip.open(p, 'rt', encoding='utf-8') as fh:  # type: ignore[arg-type]
                    data = json.load(fh)
            else:
                data = json.loads(p.read_text(encoding='utf-8'))
        except Exception:  # noqa: BLE001
            # Remove corrupt/empty snapshot for retry semantics expected by tests
            try:
                p.unlink()
            except Exception:  # noqa: BLE001
                pass
            return None
        if isinstance(data, dict):
            arr = data.get('latencies', [])
            slo_total = data.get('slo_violation_total') or data.get('slo_p95_violation_total')
            last_reset = data.get('last_reset') or data.get('last_reset_ts')
        else:
            arr = data
            slo_total = None
            last_reset = None
        from . import conciliacion_api_clean as _clean  # import after read
        # Clear alias + primary deque (they reference same object originally)
        try:
            _clean._LATENCIES.clear()
        except Exception:  # noqa: BLE001
            pass
        clean_vals = []
        if isinstance(arr, list):
            for v in arr[-(_clean._LATENCIES.maxlen or len(arr)):]:  # type: ignore[attr-defined]
                try:
                    clean_vals.append(float(v))
                except Exception:  # noqa: BLE001
                    pass
        for v in clean_vals:
            _clean._LATENCIES.append(v)
        # Mirror into clean alias if diverged
        if _clean._SUGGEST_LATENCIES is not _clean._LATENCIES:
            try:
                _clean._SUGGEST_LATENCIES.clear()
                _clean._SUGGEST_LATENCIES.extend(_clean._LATENCIES)
            except Exception:  # noqa: BLE001
                pass
        # Also mirror into legacy shim's exported deque reference (may point to old object)
        try:
            from . import conciliacion_api as _shim_self  # self import
            if hasattr(_shim_self, '_SUGGEST_LATENCIES') and _shim_self._SUGGEST_LATENCIES is not _clean._LATENCIES:
                try:
                    _shim_self._SUGGEST_LATENCIES.clear()
                    _shim_self._SUGGEST_LATENCIES.extend(_clean._LATENCIES)
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            pass
        if slo_total is not None:
            try:
                val = int(float(slo_total))
                _clean._SLO_VIOLATIONS = val
                _clean._SUGGEST_SLO_VIOLATION_TOTAL = val
                # Mirror into shim globals
                globals()['_SUGGEST_SLO_VIOLATION_TOTAL'] = val
            except Exception:  # noqa: BLE001
                pass
        if last_reset is not None:
            try:
                ts = float(last_reset)
                _clean._RESET_TS = ts
                _clean._SUGGEST_LAT_LAST_RESET = ts
                globals()['_SUGGEST_LAT_LAST_RESET'] = ts
            except Exception:  # noqa: BLE001
                pass
        return None
    return None


__all__ = [
    "bp",
    "suggest_for_movement",
    "_load_persisted",
    "_SUGGEST_LATENCIES",
    "_SUGGEST_SLO_VIOLATION_TOTAL",
    "_SUGGEST_LAT_LAST_RESET",
]


def deprecated():  # pragma: no cover
    return {"note": "use conciliacion_api_clean instead"}


# SENTINEL (nothing should follow)

