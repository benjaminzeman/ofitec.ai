#!/usr/bin/env python3
"""Emit volatility metrics (std dev last N rows) as JSON.

Output example (fractions and pp):
{
  "window": 7,
  "rows": 7,
  "assignment_sd": 0.0123,          # fraction
  "coverage_sd": 0.0155,            # fraction
  "assignment_volatility_pp": 1.23, # percentage points
  "coverage_volatility_pp": 1.55
}

Usage:
  python tools/gen_ar_rules_volatility_json.py --history badges/ar_rules_history.csv --out badges/ar_rules_volatility.json --window 7
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import List, Tuple


def read_last(path: Path, n: int) -> List[Tuple[float, float]]:
    if not path.exists():
        return []
    rows: List[Tuple[float, float]] = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                a = float(row.get("project_assign_rate") or 0)
                c = float(row.get("customer_name_rule_coverage") or 0)
            except ValueError:
                continue
            rows.append((a, c))
    return rows[-n:]


def stdev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    var = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)


def percentile(sorted_vals: List[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if p <= 0:
        return sorted_vals[0]
    if p >= 1:
        return sorted_vals[-1]
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    d = k - f
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--history', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--window', type=int, default=7)
    args = ap.parse_args()
    rows = read_last(Path(args.history), args.window)
    assigns = [r[0] for r in rows]
    covs = [r[1] for r in rows]
    a_sd = stdev(assigns)
    c_sd = stdev(covs)
    assigns_sorted = sorted(assigns)
    covs_sorted = sorted(covs)
    a_p10 = percentile(assigns_sorted, 0.10)
    a_p90 = percentile(assigns_sorted, 0.90)
    c_p10 = percentile(covs_sorted, 0.10)
    c_p90 = percentile(covs_sorted, 0.90)
    a_p25 = percentile(assigns_sorted, 0.25)
    a_p75 = percentile(assigns_sorted, 0.75)
    c_p25 = percentile(covs_sorted, 0.25)
    c_p75 = percentile(covs_sorted, 0.75)
    out = {
        'window': args.window,
        'rows': len(rows),
        'assignment_sd': a_sd,
        'coverage_sd': c_sd,
        'assignment_volatility_pp': a_sd * 100,
        'coverage_volatility_pp': c_sd * 100,
        'assignment_p10': a_p10,
        'assignment_p90': a_p90,
        'assignment_range': (a_p90 - a_p10) if assigns_sorted else 0.0,
        'assignment_iqr': (a_p75 - a_p25) if assigns_sorted else 0.0,
        'coverage_p10': c_p10,
        'coverage_p90': c_p90,
        'coverage_range': (c_p90 - c_p10) if covs_sorted else 0.0,
        'coverage_iqr': (c_p75 - c_p25) if covs_sorted else 0.0,
    }
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, indent=2), encoding='utf-8')
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
