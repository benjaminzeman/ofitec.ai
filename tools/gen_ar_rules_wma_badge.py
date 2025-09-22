#!/usr/bin/env python3
"""Generate weighted moving average (WMA) badge for AR rules metrics.

Reads history CSV (same used by other badges) and computes a weighted moving
average for the last N rows (default 7) for both assignment rate and coverage
(rate columns: project_assign_rate, customer_name_rule_coverage). The weight
scheme is linear: 1,2,...,N (more recent rows have higher weight). If there
are fewer than 2 data rows, still generate a badge but mark WMA as 0.0.

Output SVG path example:
  badges/ar_rules_trend_wma.svg

Usage:
  python tools/gen_ar_rules_wma_badge.py --history badges/ar_rules_history.csv --out badges/ar_rules_trend_wma.svg --window 7
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List, Tuple


LABEL = "ar rules wma"
LEFT_COLOR = "#555"
# Reuse same color scale thresholds as main/trend badge for assignment WMA
# (You could compute coverage-based color, but we keep consistent with assignment focus.)
THRESHOLDS = [
    (0.90, "#2ECC71"),  # green
    (0.80, "#F1C40F"),  # yellow
    (0.70, "#E67E22"),  # orange
    (0.00, "#E74C3C"),  # red
]


def read_rates(path: Path) -> List[Tuple[float, float]]:
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
    return rows


def wma(values: List[float]) -> float:
    if not values:
        return 0.0
    weights = list(range(1, len(values) + 1))
    total_w = sum(weights)
    return sum(v * w for v, w in zip(values, weights)) / total_w


def pick_color(value: float) -> str:
    for threshold, color in THRESHOLDS:
        if value >= threshold:
            return color
    return THRESHOLDS[-1][1]


def estimate_width(text_left: str, text_right: str) -> Tuple[int, int, int]:
    # Approx character width (monospace-ish) for our simple badge style.
    # This is heuristic; consistent with other custom badges.
    # ~6px per char plus some padding.
    left_w = 6 * len(text_left) + 10
    right_w = 6 * len(text_right) + 10
    return left_w, right_w, left_w + right_w


def build_svg(label: str, value_text: str, color: str) -> str:
    left_w, right_w, total_w = estimate_width(label, value_text)
    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='{total_w}' height='20' role='img' aria-label='{label}: {value_text}'>
  <linearGradient id='smooth' x2='0' y2='100%'>
    <stop offset='0' stop-color='#fff' stop-opacity='.7'/>
    <stop offset='0.1' stop-color='#aaa' stop-opacity='.1'/>
    <stop offset='0.9' stop-color='#000' stop-opacity='.3'/>
    <stop offset='1' stop-color='#000' stop-opacity='.5'/>
  </linearGradient>
  <mask id='round'>
    <rect width='{total_w}' height='20' rx='3' fill='#fff'/>
  </mask>
  <g mask='url(#round)'>
    <rect width='{left_w}' height='20' fill='{LEFT_COLOR}'/>
    <rect x='{left_w}' width='{right_w}' height='20' fill='{color}'/>
    <rect width='{total_w}' height='20' fill='url(#smooth)'/>
  </g>
  <g fill='#fff' text-anchor='middle' font-family='DejaVu Sans,Verdana,Geneva,sans-serif' font-size='11'>
    <text x='{left_w / 2}' y='14'>{label}</text>
    <text x='{left_w + right_w / 2}' y='14'>{value_text}</text>
  </g>
</svg>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--history", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--window", type=int, default=7, help="Number of recent rows for WMA")
    args = ap.parse_args()

    rows = read_rates(Path(args.history))
    if not rows:
        wma_assign = 0.0
        wma_cov = 0.0
    else:
        window_rows = rows[-args.window :]
        assigns = [r[0] for r in window_rows]
        covs = [r[1] for r in window_rows]
        wma_assign = wma(assigns)
        wma_cov = wma(covs)

    # Provide both assignment and coverage in value text.
    value_text = f"assign {wma_assign:.1%} | cov {wma_cov:.1%}"
    color = pick_color(wma_assign)
    svg = build_svg(LABEL, value_text, color)

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(svg, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
