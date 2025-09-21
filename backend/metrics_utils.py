"""Utility math helpers for reconciliation metrics (percentiles, histograms).

Separated from conciliacion_api_clean to simplify testing and reuse.
"""
from __future__ import annotations

from typing import List, Tuple, TypedDict


class LatencyQuantiles(TypedDict):
    count: float
    sum: float
    avg: float
    p50: float
    p95: float
    p99: float


class LatencySummaryResult(TypedDict):
    summary: LatencyQuantiles
    histogram: List[Tuple[float, int]]
    violations: int


def percentile(sorted_vals: List[float], q: float) -> float:
    """Return the q quantile (0<=q<=1) using linear interpolation.

    Expects input already sorted to avoid repeated sorting.
    """
    if not sorted_vals:
        return 0.0
    if q <= 0:
        return sorted_vals[0]
    if q >= 1:
        return sorted_vals[-1]
    idx = (len(sorted_vals) - 1) * q
    lo = int(idx)
    hi = min(len(sorted_vals) - 1, lo + 1)
    if lo == hi:
        return sorted_vals[lo]
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def histogram(values: List[float], buckets: List[float]) -> List[Tuple[float, int]]:
    """Return cumulative histogram counts.

    Adds a final (+inf, total) bucket for convenience.
    """
    counts = [0 for _ in buckets]
    total = 0
    for v in values:
        total += 1
        for i, b in enumerate(buckets):
            if v <= b:
                counts[i] += 1
    out: List[Tuple[float, int]] = list(zip(buckets, counts))
    out.append((float('inf'), total))
    return out


def compute_latency_summary(values: List[float], buckets: List[float], slo_p95: float = 0.0) -> LatencySummaryResult:
    """Compute summary + histogram + SLO violations (pure function).

    Returns dict with keys:
      summary: {count,sum,avg,p50,p95,p99}
      histogram: [(bucket, cumulative_count), ... , (+inf,total)]
      violations: int (samples > slo_p95 if slo_p95>0)
    """
    # Normalize buckets: positive, sorted, unique (cast to float)
    norm_buckets: List[float] = sorted({float(b) for b in buckets if isinstance(b, (int, float)) and b > 0})
    if not values:
        hist_empty: List[Tuple[float, int]] = [(b, 0) for b in norm_buckets]
        hist_empty.append((float('inf'), 0))
        return {
            "summary": {"count": 0, "sum": 0.0, "avg": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0},
            "histogram": hist_empty,
            "violations": 0,
        }
    srt = sorted(values)
    total = sum(srt)
    count = len(srt)
    avg = total / count
    p50 = percentile(srt, 0.50)
    p95 = percentile(srt, 0.95)
    p99 = percentile(srt, 0.99)
    if p95 < avg:
        p95 = avg
    if p99 < p95:
        p99 = p95
    hist = histogram(srt, norm_buckets)
    violations = 0
    if slo_p95 > 0:
        # since srt sorted ascending, find first index > slo_p95
        # simple linear scan acceptable (small window); optimize later if needed
        violations = sum(1 for v in srt if v > slo_p95)
    return {
        "summary": {"count": float(count), "sum": total, "avg": avg, "p50": p50, "p95": p95, "p99": p99},
        "histogram": hist,
        "violations": violations,
    }


__all__ = [
    "percentile",
    "histogram",
    "compute_latency_summary",
    "LatencySummaryResult",
    "LatencyQuantiles",
]
