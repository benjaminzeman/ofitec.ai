#!/usr/bin/env python3
"""Generate volatility badge (standard deviation over last N values).

Computes standard deviation for assignment rate and coverage over the last N
entries of the history CSV and displays combined volatility summary.

Output example: badges/ar_rules_volatility.svg
Label: ar vol
Value: sd assign X.Y pp | cov Z.W pp  (pp = percentage points)

If fewer than 2 samples -> volatility 0.0.

Usage:
  python tools/gen_ar_rules_volatility_badge.py --history badges/ar_rules_history.csv --out badges/ar_rules_volatility.svg --window 7
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import List, Tuple

LEFT_COLOR = "#555"
LABEL = "ar vol"


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


def estimate_width(left: str, right: str) -> Tuple[int, int, int]:
    lw = 6 * len(left) + 10
    rw = 6 * len(right) + 10
    return lw, rw, lw + rw


def pick_color(sd_assign_pp: float) -> str:
    # assignment volatility in percentage points
    if sd_assign_pp < 2:
        return "#2ECC71"  # low volatility
    if sd_assign_pp < 4:
        return "#F1C40F"  # moderate
    if sd_assign_pp < 6:
        return "#E67E22"  # elevated
    return "#E74C3C"      # high


def build_svg(assign_sd: float, cov_sd: float) -> str:
    # convert fractions to pp
    assign_pp = assign_sd * 100
    cov_pp = cov_sd * 100
    value = f"sd assign {assign_pp:.1f}pp | cov {cov_pp:.1f}pp"
    color = pick_color(assign_pp)
    lw, rw, total = estimate_width(LABEL, value)
    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='{total}' height='20' role='img' aria-label='{LABEL}: {value}'>
  <linearGradient id='smooth' x2='0' y2='100%'>
    <stop offset='0' stop-color='#fff' stop-opacity='.7'/>
    <stop offset='0.1' stop-color='#aaa' stop-opacity='.1'/>
    <stop offset='0.9' stop-color='#000' stop-opacity='.3'/>
    <stop offset='1' stop-color='#000' stop-opacity='.5'/>
  </linearGradient>
  <mask id='round'>
    <rect width='{total}' height='20' rx='3' fill='#fff'/>
  </mask>
  <g mask='url(#round)'>
    <rect width='{lw}' height='20' fill='{LEFT_COLOR}'/>
    <rect x='{lw}' width='{rw}' height='20' fill='{color}'/>
    <rect width='{total}' height='20' fill='url(#smooth)'/>
  </g>
  <g fill='#fff' text-anchor='middle' font-family='DejaVu Sans,Verdana,Geneva,sans-serif' font-size='11'>
    <text x='{lw/2}' y='14'>{LABEL}</text>
    <text x='{lw + rw/2}' y='14'>{value}</text>
  </g>
</svg>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--history', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--window', type=int, default=7)
    ap.add_argument('--emit-github-output', default=None, help='Path to $GITHUB_OUTPUT to write volatility pp values')
    args = ap.parse_args()
    rows = read_last(Path(args.history), args.window)
    assigns = [r[0] for r in rows]
    covs = [r[1] for r in rows]
    assign_sd = stdev(assigns)
    cov_sd = stdev(covs)
    svg = build_svg(assign_sd, cov_sd)
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(svg, encoding='utf-8')
    if args.emit_github_output:
        # expose pp (percentage points) values with 1 decimal
        with open(args.emit_github_output, 'a', encoding='utf-8') as gh:
            gh.write(f"assignment_volatility_pp={assign_sd*100:.1f}\n")
            gh.write(f"coverage_volatility_pp={cov_sd*100:.1f}\n")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
