#!/usr/bin/env python3
"""Generate an SVG badge for AR rules coverage.

Inputs:
  --stats path/to/ar_rules_stats.json (output of ar_rules_stats.py)
  --out   output SVG path
  --emit-github-output $GITHUB_OUTPUT (optional) writes key=value lines:
      project_assign_rate_pct
      customer_name_rule_coverage_pct
Design aims: zero external deps, tolerant to missing fields.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

def pct(val) -> float:
    try:
        v = float(val or 0)
        if v < 0:
            return 0.0
        if v > 1:
            # assume already percent
            return v
        return v * 100
    except Exception:  # noqa: BLE001
        return 0.0

def pick_color(rate_pct: float) -> str:
    if rate_pct >= 80:  # brightgreen
        return "4c1"
    if rate_pct >= 60:
        return "2c7"
    if rate_pct >= 40:
        return "dfb317"  # yellow
    if rate_pct >= 20:
        return "fe7d37"  # orange
    return "e05d44"      # red

def build_svg(assign_pct: float, name_cov_pct: float) -> str:
    label = "AR Rules"
    value = f"{assign_pct:.1f}% / {name_cov_pct:.1f}%"
    label_width = 70
    value_width = max(60, 110 + len(value) * 6 - label_width)
    total = label_width + value_width
    color = pick_color(assign_pct)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="20" role="img" aria-label="{label}: {value}">
  <linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>
  <mask id="m"><rect width="{total}" height="20" rx="3" fill="#fff"/></mask>
  <g mask="url(#m)">
    <rect width="{label_width}" height="20" fill="#555"/>
    <rect x="{label_width}" width="{value_width}" height="20" fill="#{color}"/>
    <rect width="{total}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="{label_width/2:.0f}" y="15" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{label_width/2:.0f}" y="14">{label}</text>
    <text x="{label_width + value_width/2:.0f}" y="15" fill="#010101" fill-opacity=".3">{value}</text>
    <text x="{label_width + value_width/2:.0f}" y="14">{value}</text>
  </g>
</svg>'''

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--emit-github-output", default=None)
    args = ap.parse_args()
    stats_path = Path(args.stats)
    if not stats_path.exists():
        raise SystemExit("stats JSON not found: " + str(stats_path))
    data = json.loads(stats_path.read_text(encoding="utf-8"))
    assign_pct = pct(data.get("project_assign_rate"))
    name_cov_pct = pct(data.get("customer_name_rule_coverage"))
    svg = build_svg(assign_pct, name_cov_pct)
    Path(args.out).write_text(svg, encoding="utf-8")
    if args.emit_github_output:
        with open(args.emit_github_output, "a", encoding="utf-8") as gh:
            gh.write(f"project_assign_rate_pct={assign_pct:.1f}\n")
            gh.write(f"customer_name_rule_coverage_pct={name_cov_pct:.1f}\n")
    return 0

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
