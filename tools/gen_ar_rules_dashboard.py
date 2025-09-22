#!/usr/bin/env python3
"""Generate a simple HTML dashboard aggregating AR rules metrics artifacts.

Inputs:
  --stats badges/ar_rules_stats.json
  --history badges/ar_rules_history.csv
  --weekly badges/ar_rules_weekly.json (optional)
  --out badges/ar_rules_dashboard.html
  --window 30 (days/rows to preview from history)

The dashboard embeds current stats JSON (pretty), shows a small table of the
most recent N history rows (no heavy JS), and links/embeds all SVG badges if
present.

This is intentionally minimal (no external CSS) to allow publishing via raw
GitHub (or Pages) without CSP concerns.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import List, Dict


def read_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def read_history(path: Path, limit_rows: int) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    out: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            out.append(row)
    return out[-limit_rows:]


def build_html(stats: Dict, history: List[Dict[str, str]], weekly: Dict, badge_paths: List[str], vol_json: Dict) -> str:
    def esc(s: str) -> str:
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    stats_pre = esc(json.dumps(stats, indent=2))
    weekly_pre = esc(json.dumps(weekly, indent=2)) if weekly else "{}"

    hist_rows = "".join(
        f"<tr><td>{esc(r.get('timestamp', ''))}</td><td>{esc(r.get('project_assign_rate', ''))}</td><td>{esc(r.get('customer_name_rule_coverage', ''))}</td></tr>"
        for r in history
    )

    badges_html = []
    for bp in badge_paths:
        if Path(bp).exists():
            # Use relative path; embed via img tag
            badges_html.append(f"<div class='badge'><img src='{bp}' alt='{bp}'/></div>")
    badges_section = "".join(badges_html) or "<em>No badges found.</em>"

    volatility_block = ""
    if vol_json:
        try:
            av = vol_json.get('assignment_volatility_pp')
            cv = vol_json.get('coverage_volatility_pp')
            rows = vol_json.get('rows')
            window = vol_json.get('window')
            volatility_block = f"<div class='meta'>Volatility: assign {av:.2f}pp | coverage {cv:.2f}pp (rows={rows}, window={window})</div>"
        except Exception:  # noqa: BLE001
            volatility_block = ""

    css = r"""
body { font-family: system-ui, Arial, sans-serif; margin: 1.5rem; background:#f7f9fb; color:#222; }
header h1 { margin:0 0 .5rem 0; font-size:1.6rem; }
section { margin-bottom:2rem; }
.badges { display:flex; flex-wrap:wrap; gap:8px; align-items:center; }
.badge img { height:20px; border:1px solid #ddd; border-radius:4px; background:#fff; padding:2px 4px; }
pre { background:#1e1e1e; color:#eee; padding:1rem; overflow:auto; border-radius:6px; }
table { border-collapse: collapse; width:100%; background:#fff; }
th, td { padding:4px 6px; border:1px solid #ccc; font-size:0.85rem; }
th { background:#e8eef3; text-align:left; }
.meta { font-size:0.8rem; color:#555; }
"""

    return f"""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='utf-8'/>
<title>AR Rules Dashboard</title>
<style>{css}</style>
</head>
<body>
<header>
  <h1>AR Rules Metrics Dashboard</h1>
  <div class='meta'>Generated from repository artifacts.</div>
</header>
<section>
    <h2>Badges</h2>
    <div class='badges'>{badges_section}</div>
    {volatility_block}
</section>
<section>
  <h2>Current Stats JSON</h2>
  <pre>{stats_pre}</pre>
</section>
<section>
  <h2>Weekly Aggregation</h2>
  <pre>{weekly_pre}</pre>
</section>
<section>
  <h2>Recent History</h2>
  <table>
    <thead><tr><th>timestamp</th><th>assign_rate</th><th>coverage</th></tr></thead>
    <tbody>{hist_rows}</tbody>
  </table>
</section>
<footer class='meta'>Auto-generated dashboard. Customize styles or add charts in future iterations.</footer>
</body>
</html>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--stats', required=True)
    ap.add_argument('--history', required=True)
    ap.add_argument('--weekly', required=False, default=None)
    ap.add_argument('--out', required=True)
    ap.add_argument('--window', type=int, default=30)
    args = ap.parse_args()

    stats = read_json(Path(args.stats))
    weekly = read_json(Path(args.weekly)) if args.weekly else {}
    history = read_history(Path(args.history), args.window)

    badge_paths = [
        'badges/ar_rules_coverage.svg',
        'badges/ar_rules_coverage_only.svg',
        'badges/ar_rules_trend.svg',
        'badges/ar_rules_trend_wma.svg',
        'badges/ar_rules_volatility.svg',
        'badges/ar_rules_thresholds.svg',
        'badges/ar_rules_sparkline.svg',
        'badges/ar_rules_streak.svg',
    ]

    vol_json = read_json(Path('badges/ar_rules_volatility.json'))

    html = build_html(stats, history, weekly, badge_paths, vol_json)
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(html, encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
