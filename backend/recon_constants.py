"""Shared reconciliation (conciliación) constants and tunables.

Env overrides (optional):
  RECON_ALIAS_MAX_LEN -> int (default 120)
  RECON_SUGGEST_MIN_LIMIT -> int (default 1)
  RECON_SUGGEST_MAX_LIMIT -> int (default 50)
  RECON_SUGGEST_DEFAULT_LIMIT -> int (default 5)

Values are clamped to sane ranges to avoid pathological configs.
"""
from __future__ import annotations

import os


def _coerce_int(env_key: str, default: int) -> int:
    try:
        raw = os.getenv(env_key)
        if raw is None:
            return default
        return int(raw)
    except Exception:  # pragma: no cover - defensive
        return default


ALIAS_MAX_LEN = max(10, min(512, _coerce_int("RECON_ALIAS_MAX_LEN", 120)))

SUGGEST_MIN_LIMIT = max(1, min(10, _coerce_int("RECON_SUGGEST_MIN_LIMIT", 1)))
SUGGEST_MAX_LIMIT = max(
    SUGGEST_MIN_LIMIT,
    min(100, _coerce_int("RECON_SUGGEST_MAX_LIMIT", 50)),
)
SUGGEST_DEFAULT_LIMIT = max(
    SUGGEST_MIN_LIMIT,
    min(SUGGEST_MAX_LIMIT, _coerce_int("RECON_SUGGEST_DEFAULT_LIMIT", 5)),
)

__all__ = [
    "ALIAS_MAX_LEN",
    "SUGGEST_MIN_LIMIT",
    "SUGGEST_MAX_LIMIT",
    "SUGGEST_DEFAULT_LIMIT",
    "AP_CONFIDENCE_BUCKET_EDGES",
    "ap_confidence_bucket_labels",
]

# AP confidence bucket edges (inclusive upper bounds) used for histogram-style distribution.
# These were originally hard-coded in api_matching_metrics; centralized here for reuse and
# easier future tuning. Maintain sorted order and final 1.0 upper bound.
AP_CONFIDENCE_BUCKET_EDGES: list[float] = [0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 1.0]

 
def ap_confidence_bucket_labels() -> list[str]:
    """Return textual bucket labels matching the 5-digit scaled left/right bounds used in metrics.

    Format: 'LLLLL_RRRRR' where values are the float bounds * 10000, zero-padded to 5 digits.
    Example: 0.0-0.2 -> '00000_02000'. The implementation relies on AP_CONFIDENCE_BUCKET_EDGES.
    """
    edges = AP_CONFIDENCE_BUCKET_EDGES
    labels: list[str] = []
    prev = 0.0
    for e in edges:
        left = int(round(prev * 10000))
        right = int(round(e * 10000))
        labels.append(f"{left:05d}_{right:05d}")
        prev = e
    return labels
