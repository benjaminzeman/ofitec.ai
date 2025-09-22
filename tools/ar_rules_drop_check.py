#!/usr/bin/env python3
"""Utility to detect drops (in percentage points) between current and previous AR rules stats for a numeric fraction field.

Usage:
  python tools/ar_rules_drop_check.py \
      --current badges/ar_rules_stats.json \
      --previous badges/prev_ar_rules_stats.json \
      --out-meta badges/drop_meta.json \
      [--alert-file badge_drop_alert.txt] \
      [--threshold-pp 5] [--fail]

Semantics:
  - Reads current and (optional) previous stats JSON (same shape as produced by ar_rules_stats.py).
    - Computes drop = prev[field] - cur[field] (fraction) if both present.
  - If drop * 100 >= threshold_pp AND prev>0: writes alert text file and exits with code 2 when --fail set.
  - Always writes metadata JSON with prev, cur, drop_fraction, drop_pp, threshold_pp, alerted(bool).
Exit Codes:
  0: OK (no alert)
  1: Non fatal issues (missing current file or parse error)
  2: Alert triggered and --fail provided
"""
from __future__ import annotations
import argparse
import json
import sys
import os
import datetime as dt
from typing import Any, Dict


def read_json(path: str) -> Dict[str, Any] | None:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:  # pragma: no cover - defensive
        print(f"WARN: failed reading {path}: {e}", file=sys.stderr)
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--current', required=True)
    ap.add_argument('--previous', required=False, default=None)
    ap.add_argument('--out-meta', required=True)
    ap.add_argument('--alert-file', required=False, default='badge_drop_alert.txt')
    ap.add_argument('--field', default='project_assign_rate', help='Field key in JSON stats to compare (fraction 0..1)')
    ap.add_argument('--threshold-pp', type=float, default=5.0, help='Threshold drop in percentage points')
    ap.add_argument('--fail', action='store_true', help='Exit with code 2 if alert triggered')
    args = ap.parse_args()

    cur = read_json(args.current)
    if not cur:
        print('ERROR: current stats JSON missing or invalid', file=sys.stderr)
        return 1
    prev = read_json(args.previous) if args.previous else None

    cur_rate = cur.get(args.field) or 0.0
    prev_rate = (prev or {}).get(args.field) or 0.0
    drop_fraction = max(0.0, prev_rate - cur_rate)
    drop_pp = drop_fraction * 100.0

    alerted = prev_rate > 0 and drop_pp >= args.threshold_pp

    meta = {
        'generated_at': dt.datetime.utcnow().isoformat() + 'Z',
        'field': args.field,
        'prev': prev_rate,
        'cur': cur_rate,
        'drop_fraction': drop_fraction,
        'drop_pp': drop_pp,
        'threshold_pp': args.threshold_pp,
        'alerted': alerted,
        'fail_mode': bool(args.fail),
    }
    os.makedirs(os.path.dirname(args.out_meta) or '.', exist_ok=True)
    with open(args.out_meta, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)

    if alerted:
        alert_text = (
            f"Field '{args.field}' dropped {drop_pp:.2f} pp "
            f"(prev {prev_rate*100:.2f}%, now {cur_rate*100:.2f}%) >= threshold {args.threshold_pp:.2f} pp"
        )
        with open(args.alert_file, 'w', encoding='utf-8') as af:
            af.write(alert_text + '\n')
        print(alert_text, file=sys.stderr)
        if args.fail:
            return 2
    else:
        print(f"No significant drop (prev={prev_rate*100:.2f}%, cur={cur_rate*100:.2f}%, drop_pp={drop_pp:.2f}).")
    return 0


if __name__ == '__main__':
    sys.exit(main())
