#!/usr/bin/env python3
"""Generate a synthetic AR rules history CSV for local experimentation.

This helper lets you quickly bootstrap `badges/ar_rules_history.csv` with
plausible values so that the badge scripts (trend, WMA, volatility, weekly
aggregation, dashboard) can be previewed sin necesidad de esperar días reales.

Columns generadas (idénticas al workflow real):
  timestamp,project_assign_rate,customer_name_rule_coverage

Por defecto crea 30 días (filas) retrospectivos hasta hoy (UTC) con una base
inicial de asignación y cobertura y aplica un *drift* pequeño según el modo y
ruido aleatorio controlado. La semilla se puede fijar para reproducibilidad.

Modos (`--mode`):
  stable      -> Drift ~0, ruido bajo (default)
  improving   -> Drift positivo (lineal) ligero
  declining   -> Drift negativo ligero
  volatile    -> Drift ~0 pero ruido más alto (simula dispersión)

Ejemplos:
  python tools/gen_ar_rules_fake_history.py --out badges/ar_rules_history.csv
  python tools/gen_ar_rules_fake_history.py --days 60 --mode improving --seed 123
  python tools/gen_ar_rules_fake_history.py --start-date 2025-08-01 --days 10 --mode volatile

No depende de librerías externas.
"""
from __future__ import annotations

import argparse
import datetime as dt
import random
from pathlib import Path

MODES = {"stable", "improving", "declining", "volatile"}


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def generate_series(
    days: int,
    mode: str,
    assign_start: float,
    cov_start: float,
    seed: int | None,
) -> list[tuple[str, float, float]]:
    if seed is not None:
        random.seed(seed)
    today = dt.datetime.utcnow().date()
    # start_date retrocede days-1 (inclusive)
    start_date = today - dt.timedelta(days=days - 1)

    # Parámetros de drift y ruido por modo
    if mode == "improving":
        assign_drift = 0.0009  # ~0.09 pp / día
        cov_drift = 0.0011     # ~0.11 pp / día
        noise_scale_a = 0.005
        noise_scale_c = 0.006
    elif mode == "declining":
        assign_drift = -0.0008
        cov_drift = -0.0010
        noise_scale_a = 0.005
        noise_scale_c = 0.006
    elif mode == "volatile":
        assign_drift = 0.0
        cov_drift = 0.0
        noise_scale_a = 0.015  # mayor dispersión
        noise_scale_c = 0.018
    else:  # stable
        assign_drift = 0.0001
        cov_drift = 0.0001
        noise_scale_a = 0.004
        noise_scale_c = 0.005

    rows: list[tuple[str, float, float]] = []
    a = assign_start
    c = cov_start
    for i in range(days):
        d = start_date + dt.timedelta(days=i)
        # aplicar drift lineal incremental
        a += assign_drift
        c += cov_drift
        # ruido gaussiano truncado simple
        a += random.uniform(-noise_scale_a, noise_scale_a)
        c += random.uniform(-noise_scale_c, noise_scale_c)
        a = clamp(a)
        c = clamp(c)
        # timestamp estilo workflow: inicio del día + 05:00Z aprox (coincide con cron) o medianoche?
        ts = dt.datetime(d.year, d.month, d.day, 5, 0, 0, tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z")
        rows.append((ts, a, c))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="Ruta CSV de salida (se sobrescribe salvo --append)")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--mode", default="stable", choices=sorted(MODES))
    ap.add_argument("--assign-start", type=float, default=0.65, help="Valor inicial fraccional (0..1)")
    ap.add_argument("--cov-start", type=float, default=0.55, help="Valor inicial fraccional (0..1)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--append", action="store_true", help="Si existe, agrega filas nuevas que no colisionen en timestamp")
    args = ap.parse_args()

    outp = Path(args.out)
    rows = generate_series(args.days, args.mode, args.assign_start, args.cov_start, args.seed)

    header = "timestamp,project_assign_rate,customer_name_rule_coverage"\
        if not outp.exists() or not args.append else None

    if args.append and outp.exists():
        # Evitar duplicados de timestamp (hash por ts)
        existing_ts: set[str] = set()
        for line in outp.read_text(encoding="utf-8").splitlines()[1:]:
            if not line.strip():
                continue
            existing_ts.add(line.split(",", 1)[0])
        new_lines = []
        for ts, a, c in rows:
            if ts in existing_ts:
                continue
            new_lines.append(f"{ts},{a:.4f},{c:.4f}")
        with outp.open("a", encoding="utf-8") as f:
            for line in new_lines:
                f.write(line + "\n")
    else:
        outp.parent.mkdir(parents=True, exist_ok=True)
        with outp.open("w", encoding="utf-8") as f:
            if header:
                f.write(header + "\n")
            for ts, a, c in rows:
                f.write(f"{ts},{a:.4f},{c:.4f}\n")
    print(f"Synthetic history written: {outp} ({args.days} days, mode={args.mode})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
