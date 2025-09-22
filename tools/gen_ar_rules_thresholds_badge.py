#!/usr/bin/env python3
"""Generate a badge reflecting dynamic drop thresholds in pp.

Inputs are provided via CLI flags (so we can call this after threshold calc):
  --assign N   (pp)
  --coverage M (pp)
  --mode off|sensitive|lenient

Example output text: mode sensitive | assign 4pp | cov 4pp

Usage:
  python tools/gen_ar_rules_thresholds_badge.py --assign 5 --coverage 5 --mode off --out badges/ar_rules_thresholds.svg
"""
from __future__ import annotations

import argparse
from pathlib import Path

LEFT_COLOR = "#555"
LABEL = "ar thr"


def estimate_width(left: str, right: str) -> tuple[int, int, int]:
    lw = 6 * len(left) + 10
    rw = 6 * len(right) + 10
    return lw, rw, lw + rw


def pick_color(mode: str) -> str:
    if mode == 'sensitive':
        return '#2E86C1'
    if mode == 'lenient':
        return '#AF7AC5'
    return '#6C757D'  # off / default


def build_svg(mode: str, assign_pp: int, cov_pp: int) -> str:
    value = f"mode {mode} | assign {assign_pp}pp | cov {cov_pp}pp"
    lw, rw, total = estimate_width(LABEL, value)
    color = pick_color(mode)
    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='{total}' height='20' role='img' aria-label='{LABEL}: {value}'>
  <linearGradient id='smooth' x2='0' y2='100%'>
    <stop offset='0' stop-color='#fff' stop-opacity='.7'/>
    <stop offset='0.1' stop-color='#aaa' stop-opacity='.1'/>
    <stop offset='0.9' stop-color='#000' stop-opacity='.3'/>
    <stop offset='1' stop-color='#000' stop-opacity='.5'/>
  </linearGradient>
  <mask id='round'><rect width='{total}' height='20' rx='3' fill='#fff'/></mask>
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
    ap.add_argument('--assign', type=int, required=True)
    ap.add_argument('--coverage', type=int, required=True)
    ap.add_argument('--mode', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    svg = build_svg(args.mode, args.assign, args.coverage)
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(svg, encoding='utf-8')
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
