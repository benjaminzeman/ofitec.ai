#!/usr/bin/env python3
"""Generate weekly aggregation JSON (rolling 7 rows) from history CSV.

Input CSV columns: timestamp,project_assign_rate,customer_name_rule_coverage
Output JSON keys:
  window_size, rows, assign_min, assign_max, assign_avg, coverage_min, coverage_max, coverage_avg
If fewer than 2 data rows exist (excluding header), still outputs with null averages.

Usage:
  python tools/gen_ar_rules_weekly_agg.py --history badges/ar_rules_history.csv --out badges/ar_rules_weekly.json
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from typing import List, Tuple


def read_last(path: Path, n: int) -> List[Tuple[float, float]]:
    if not path.exists():
        return []
    out = []
    with path.open('r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                a = float(row.get('project_assign_rate') or 0)
                c = float(row.get('customer_name_rule_coverage') or 0)
            except ValueError:
                continue
            out.append((a, c))
    return out[-n:]


def aggregate(rows: List[Tuple[float, float]]):
    if not rows:
        return {
            'window_size': 0,
            'rows': 0,
            'assign_min': None,
            'assign_max': None,
            'assign_avg': None,
            'coverage_min': None,
            'coverage_max': None,
            'coverage_avg': None,
        }
    assigns = [r[0] for r in rows]
    covs = [r[1] for r in rows]
    return {
        'window_size': len(rows),
        'rows': len(rows),
        'assign_min': min(assigns),
        'assign_max': max(assigns),
        'assign_avg': sum(assigns)/len(assigns),
        'coverage_min': min(covs),
        'coverage_max': max(covs),
        'coverage_avg': sum(covs)/len(covs),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--history', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--window', type=int, default=7)
    args = ap.parse_args()
    rows = read_last(Path(args.history), args.window)
    agg = aggregate(rows)
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(agg, indent=2), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
