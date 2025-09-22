#!/usr/bin/env python3
"""Generate a badge (SVG) for 7-day rolling averages of AR assignment & coverage.

Reads a history CSV produced by the stats workflow with columns:
  timestamp,project_assign_rate,customer_name_rule_coverage

By default computes simple arithmetic mean of last <=7 rows (chronological order ignored beyond row selection).
If fewer than 2 rows exist, marks the badge as 'n/a'.

Outputs an SVG similar styling to shields.io (basic flat style) with two numbers:
  Assign 83.2%  |  Cov 77.5%

Usage:
  python tools/gen_ar_rules_trend_badge.py --history badges/ar_rules_history.csv --out badges/ar_rules_trend.svg
"""
from __future__ import annotations
import argparse
import csv
from pathlib import Path
from typing import List, Tuple

BADGE_TEMPLATE = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='20' role='img' aria-label='AR Trend: {label_values}'>"
    "\n  <linearGradient id='smooth' x2='0' y2='100%'>"
    "\n    <stop offset='0' stop-color='#bbb' stop-opacity='.1'/>"
    "\n    <stop offset='1' stop-opacity='.1'/>"
    "\n  </linearGradient>"
    "\n  <mask id='round'>"
    "\n    <rect width='{w}' height='20' rx='3' fill='#fff'/>"
    "\n  </mask>"
    "\n  <g mask='url(#round)'>"
    "\n    <rect width='{left_w}' height='20' fill='#555'/>"
    "\n    <rect x='{left_w}' width='{right_w}' height='20' fill='{color}'/>"
    "\n    <rect width='{w}' height='20' fill='url(#smooth)'/>"
    "\n  </g>"
    "\n  <g fill='#fff' text-anchor='middle' font-family='Verdana,Geneva,DejaVu Sans,sans-serif' font-size='11'>"
    "\n    <text x='{left_w_mid}' y='15' fill='#010101' fill-opacity='.3'>AR 7d</text>"
    "\n    <text x='{left_w_mid}' y='14'>AR 7d</text>"
    "\n    <text x='{right_mid}' y='15' fill='#010101' fill-opacity='.3'>{values}</text>"
    "\n    <text x='{right_mid}' y='14'>{values}</text>"
    "\n  </g>"
    "\n</svg>"
)

COLOR_THRESHOLDS = [
    (0.90, '#4c1'),  # bright green
    (0.80, '#97CA00'),
    (0.70, '#dfb317'),
    (0.50, '#fe7d37'),
    (0.00, '#e05d44'),
]


def pick_color(assign_avg: float) -> str:
    for th, color in COLOR_THRESHOLDS:
        if assign_avg >= th:
            return color
    return '#555'


def read_last_rows(path: Path, n: int) -> List[Tuple[float, float]]:
    rows: List[Tuple[float, float]] = []
    if not path.exists():
        return rows
    with path.open('r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                a = float(r.get('project_assign_rate') or 0)
                c = float(r.get('customer_name_rule_coverage') or 0)
                rows.append((a, c))
            except ValueError:
                continue
    return rows[-n:]


def format_pct(v: float) -> str:
    return f"{v*100:.1f}%"


def build_svg(assign_avg: float, cov_avg: float) -> str:
    values = f"Assign {format_pct(assign_avg)} | Cov {format_pct(cov_avg)}"
    color = pick_color(assign_avg)
    left_text = 'AR 7d'
    # Very rough width calc: char width ~ 7 px average (monospaced-ish assumption)
    left_w = max(40, len(left_text) * 7 + 10)
    right_w = max(120, len(values) * 7 + 10)
    total_w = left_w + right_w
    return BADGE_TEMPLATE.format(
        w=total_w,
        left_w=left_w,
        right_w=right_w,
        left_w_mid=left_w / 2,
        right_mid=left_w + right_w / 2,
        values=values,
        color=color,
        label_values=values,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--history', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--window', type=int, default=7, help='Number of last rows to average (default 7)')
    args = ap.parse_args()

    rows = read_last_rows(Path(args.history), args.window)
    if len(rows) < 2:
        # Not enough data
        svg = build_svg(0.0, 0.0).replace('Assign 0.0% | Cov 0.0%', 'n/a')
    else:
        assign_avg = sum(r[0] for r in rows) / len(rows)
        cov_avg = sum(r[1] for r in rows) / len(rows)
        svg = build_svg(assign_avg, cov_avg)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg, encoding='utf-8')
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
