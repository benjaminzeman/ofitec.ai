#!/usr/bin/env python3
"""Generate a minimalist sparkline badge for assignment & coverage history.

Two tiny polylines (assignment = green, coverage = purple) scaled to 0..1 of the
provided window (default last 30 rows). Shows latest values as text.

Usage:
  python tools/gen_ar_rules_sparkline_badge.py --history badges/ar_rules_history.csv --out badges/ar_rules_sparkline.svg --window 30
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List, Tuple

WIDTH = 220
HEIGHT = 40
PAD = 4


def read_last(path: Path, n: int) -> List[Tuple[float, float]]:
    if not path.exists():
        return []
    rows: List[Tuple[float, float]] = []
    with path.open('r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                a = float(row.get('project_assign_rate') or 0)
                c = float(row.get('customer_name_rule_coverage') or 0)
            except ValueError:
                continue
            rows.append((a, c))
    return rows[-n:]


def scale_points(values: List[float]) -> List[Tuple[float, float]]:
    if not values:
        return []
    # Already fractions 0..1; just scale to height minus padding
    w_area = WIDTH - 2 * PAD
    h_area = HEIGHT - 2 * PAD
    n = len(values)
    if n == 1:
        return [(PAD + w_area / 2, PAD + h_area * (1 - values[0]))]
    pts = []
    for i, v in enumerate(values):
        x = PAD + (w_area * i / (n - 1))
        y = PAD + h_area * (1 - v)  # invert so higher v is higher on svg
        pts.append((x, y))
    return pts


def polyline(points: List[Tuple[float, float]]) -> str:
    if not points:
        return ''
    return ' '.join(f"{x:.1f},{y:.1f}" for x, y in points)


def build_svg(rows: List[Tuple[float, float]]) -> str:
    assigns = [r[0] for r in rows]
    covs = [r[1] for r in rows]
    a_pts = polyline(scale_points(assigns))
    c_pts = polyline(scale_points(covs))
    latest_a = assigns[-1] * 100 if assigns else 0.0
    latest_c = covs[-1] * 100 if covs else 0.0
    label = f"assign {latest_a:.1f}% | cov {latest_c:.1f}%"
    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='{WIDTH}' height='{HEIGHT}' role='img' aria-label='{label}'>
  <rect x='0' y='0' width='{WIDTH}' height='{HEIGHT}' rx='4' fill='#fff' stroke='#ccc'/>
  <polyline fill='none' stroke='#2ECC71' stroke-width='2' points='{a_pts}'/>
  <polyline fill='none' stroke='#8E44AD' stroke-width='2' points='{c_pts}'/>
  <text x='{WIDTH/2}' y='{HEIGHT-6}' text-anchor='middle' font-family='Verdana,Arial,sans-serif' font-size='10'>{label}</text>
</svg>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--history', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--window', type=int, default=30)
    args = ap.parse_args()
    rows = read_last(Path(args.history), args.window)
    svg = build_svg(rows)
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(svg, encoding='utf-8')
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
