#!/usr/bin/env python3
"""Generate a standalone coverage badge (SVG) for customer_name_rule_coverage.

Usage:
  python tools/gen_ar_rules_coverage_badge.py --stats badges/ar_rules_stats.json --out badges/ar_rules_coverage_only.svg

Logic:
  Reads JSON stats (same shape as ar_rules_stats.py) and extracts customer_name_rule_coverage (fraction 0..1).
  Renders a flat SVG similar to shields style.
  Color thresholds: >=0.90 bright green, >=0.8 green, >=0.7 yellow, >=0.5 orange, else red.
Exits 0 even if field missing (treats as 0)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

THRESH = [
    (0.90, '#4c1'),
    (0.80, '#97CA00'),
    (0.70, '#dfb317'),
    (0.50, '#fe7d37'),
    (0.00, '#e05d44'),
]

BADGE = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='20' role='img' aria-label='AR Coverage: {pct}'>"
    "<linearGradient id='g' x2='0' y2='100%'><stop offset='0' stop-color='#bbb' stop-opacity='.1'/><stop offset='1' stop-opacity='.1'/></linearGradient>"
    "<mask id='m'><rect width='{w}' height='20' rx='3' fill='#fff'/></mask>"
    "<g mask='url(#m)'><rect width='{lw}' height='20' fill='#555'/><rect x='{lw}' width='{rw}' height='20' fill='{color}'/>"
    "<rect width='{w}' height='20' fill='url(#g)'/></g>"
    "<g fill='#fff' text-anchor='middle' font-family='Verdana,Geneva,DejaVu Sans,sans-serif' font-size='11'>"
    "<text x='{lmid}' y='15' fill='#010101' fill-opacity='.3'>AR Coverage</text><text x='{lmid}' y='14'>AR Coverage</text>"
    "<text x='{rmid}' y='15' fill='#010101' fill-opacity='.3'>{pct}</text><text x='{rmid}' y='14'>{pct}</text>"
    "</g></svg>"
)


def color(v: float) -> str:
    for th, c in THRESH:
        if v >= th:
            return c
    return '#555'


def build_svg(frac: float) -> str:
    pct = f"{frac*100:.1f}%"
    left = 'AR Coverage'
    value = pct
    # estimate widths
    lw = max(80, len(left) * 7 + 10)
    rw = max(50, len(value) * 7 + 10)
    w = lw + rw
    return BADGE.format(w=w, lw=lw, rw=rw, color=color(frac), lmid=lw/2, rmid=lw+rw/2, pct=pct)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--stats', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    try:
        text = Path(args.stats).read_text(encoding='utf-8')
        data = json.loads(text)
    except (FileNotFoundError, json.JSONDecodeError):  # fallback to empty
        data = {}
    frac = float(data.get('customer_name_rule_coverage') or 0.0)
    svg = build_svg(frac)
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(svg, encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
