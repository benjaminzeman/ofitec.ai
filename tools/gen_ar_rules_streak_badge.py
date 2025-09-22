#!/usr/bin/env python3
"""Generate a badge summarizing current streak (up/down/flat) for assignment & coverage.

Heurística: se mira hacia atrás hasta `--window` (default 14) o hasta romper la racha.
Racha ascendente: cada valor estrictamente mayor al anterior.
Racha descendente: cada valor estrictamente menor al anterior.
Si mezcla → se detiene donde se rompe.

Texto ejemplo: "assign ↓3 | cov ↑2" (flechas unicode). Si longitud <2 se considera sin racha.

Colores:
 - Si cualquiera tiene racha descendente >=3 → rojo
 - Else si cualquiera racha ascendente >=3 → verde
 - Else gris

Uso:
  python tools/gen_ar_rules_streak_badge.py --history badges/ar_rules_history.csv --out badges/ar_rules_streak.svg
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List, Tuple

LEFT_COLOR = "#555"
LABEL = "ar streak"


def read_rates(path: Path) -> List[Tuple[float, float]]:
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
    return rows


def streak_length(values: List[float]) -> int:
    if len(values) < 2:
        return 0
    # Determine direction from last backwards
    direction = 0  # 1 up, -1 down
    length = 0
    for i in range(len(values) - 1, 0, -1):
        cur = values[i]
        prev = values[i - 1]
        if cur > prev:
            if direction in (0, 1):
                direction = 1
                length += 1
            else:
                break
        elif cur < prev:
            if direction in (0, -1):
                direction = -1
                length += 1
            else:
                break
        else:  # equal resets
            break
    # length cuenta transiciones; racha de 2 valores tiene length=1; normalizamos a número de puntos
    if length == 0:
        return 0
    return length + 1


def streak_dir(values: List[float]) -> int:
    if len(values) < 2:
        return 0
    direction = 0
    for i in range(len(values) - 1, 0, -1):
        cur = values[i]
        prev = values[i - 1]
        if cur > prev:
            if direction in (0, 1):
                direction = 1
            else:
                break
        elif cur < prev:
            if direction in (0, -1):
                direction = -1
            else:
                break
        else:
            break
    return direction


def estimate_width(left: str, right: str) -> tuple[int, int, int]:
    lw = 6 * len(left) + 10
    rw = 6 * len(right) + 10
    return lw, rw, lw + rw


def pick_color(assign_dir: int, assign_len: int, cov_dir: int, cov_len: int) -> str:
    if (assign_dir == -1 and assign_len >= 3) or (cov_dir == -1 and cov_len >= 3):
        return '#E74C3C'
    if (assign_dir == 1 and assign_len >= 3) or (cov_dir == 1 and cov_len >= 3):
        return '#2ECC71'
    return '#6C757D'


def build_value(assign_dir: int, assign_len: int, cov_dir: int, cov_len: int) -> str:
    def part(dir_: int, length: int, label: str) -> str:
        if length < 2:
            return f"{label} ·"
        arrow = '↑' if dir_ == 1 else '↓' if dir_ == -1 else '·'
        return f"{label} {arrow}{length}"
    return f"{part(assign_dir, assign_len, 'assign')} | {part(cov_dir, cov_len, 'cov')}"


def build_svg(assign_dir: int, assign_len: int, cov_dir: int, cov_len: int) -> str:
    value = build_value(assign_dir, assign_len, cov_dir, cov_len)
    lw, rw, total = estimate_width(LABEL, value)
    color = pick_color(assign_dir, assign_len, cov_dir, cov_len)
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
    ap.add_argument('--history', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--window', type=int, default=14)
    args = ap.parse_args()
    rows = read_rates(Path(args.history))
    window_rows = rows[-args.window :]
    assigns = [r[0] for r in window_rows]
    covs = [r[1] for r in window_rows]
    a_dir = streak_dir(assigns)
    c_dir = streak_dir(covs)
    a_len = streak_length(assigns)
    c_len = streak_length(covs)
    svg = build_svg(a_dir, a_len, c_dir, c_len)
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(svg, encoding='utf-8')
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
