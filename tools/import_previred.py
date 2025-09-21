#!/usr/bin/env python3
"""
Importa aportes PREVIRED desde CSV a `previred_contributions`.

Idempotencia: combinación (periodo, rut_trabajador, rut_empresa, fecha_pago, monto_total).

Uso:
  python tools/import_previred.py --csv path/to/previred.{csv|xlsx} \
    --db data/chipax_data.db \
    [--source PREVIRED]
"""

from __future__ import annotations

import argparse
import csv
import os
import sqlite3
from pathlib import Path
import sys

if __package__ in (None, ""):
    _here = Path(__file__).resolve().parent
    sys.path.append(str(_here))
from common_db import default_db_path\nfrom io_utils import load_rows
from rut_utils import normalize_rut, is_valid_rut


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS previred_contributions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          periodo TEXT,
          rut_trabajador TEXT,
          nombre_trabajador TEXT,
          rut_empresa TEXT,
          monto_total REAL,
          estado TEXT,
          fecha_pago TEXT,
          fuente TEXT
        );
        """
    )


def norm_amount(v) -> float:
    try:
        if v is None or v == "":
            return 0.0
        return float(
            str(v).replace("$", "").replace(" ", "").replace(".", "").replace(",", ".")
        )
    except Exception:
        try:
            return float(v)
        except Exception:
            return 0.0


def upsert_row(
    conn: sqlite3.Connection,
    r: dict,
    source_default: str | None,
    *,
    allow_invalid_rut: bool,
    counters: dict,
) -> None:
    cols = {c[1] for c in conn.execute("PRAGMA table_info(previred_contributions)").fetchall()}
    periodo = r.get("Periodo") or r.get("periodo")
    rut_trabajador_raw = r.get("RUT_Trabajador") or r.get("rut_trabajador") or r.get("RUT")
    rut_trabajador = normalize_rut(rut_trabajador_raw)
    nombre_trabajador = r.get("Nombre") or r.get("nombre_trabajador")
    rut_empresa_raw = r.get("RUT_Empresa") or r.get("rut_empresa")
    rut_empresa = normalize_rut(rut_empresa_raw)

    # Validación de RUTs
    for rut in (rut_trabajador, rut_empresa):
        if rut and not is_valid_rut(rut):
            if not allow_invalid_rut:
                counters["invalid_rut"] = counters.get("invalid_rut", 0) + 1
                return
    monto_total = norm_amount(r.get("Monto") or r.get("monto_total"))
    estado = r.get("Estado") or r.get("estado")
    fecha_pago = r.get("FechaPago") or r.get("fecha_pago")
    fuente = r.get("Fuente") or r.get("fuente") or source_default or "import"

    cur = conn.execute(
        (
            "SELECT 1 FROM previred_contributions WHERE periodo = ? AND IFNULL(rut_trabajador,'') = IFNULL(?, '')"
            " AND IFNULL(rut_empresa,'') = IFNULL(?, '') AND IFNULL(fecha_pago,'') = IFNULL(?, '') AND IFNULL(monto_total,0) = IFNULL(?, 0)"
        ),
        (periodo, rut_trabajador, rut_empresa, fecha_pago, monto_total),
    )
    if cur.fetchone():
        counters["duplicates"] = counters.get("duplicates", 0) + 1
        return

    insert_cols, insert_vals, insert_params = [], [], []

    def add(col, val):
        if col in cols:
            insert_cols.append(col)
            insert_vals.append("?")
            insert_params.append(val)

    for col, val in [
        ("periodo", periodo),
        ("rut_trabajador", rut_trabajador),
        ("nombre_trabajador", nombre_trabajador),
        ("rut_empresa", rut_empresa),
        ("monto_total", monto_total),
        ("estado", estado),
        ("fecha_pago", fecha_pago),
        ("fuente", fuente),
    ]:
        add(col, val)

    sql = "INSERT INTO previred_contributions (" + ", ".join(insert_cols) + ") VALUES (" + ", ".join(insert_vals) + ")"
    conn.execute(sql, insert_params)
    counters["inserted"] = counters.get("inserted", 0) + 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--db", default=default_db_path(prefer_root=False))
    ap.add_argument("--source", default="import")
    ap.add_argument("--allow-invalid-rut", action="store_true")
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print("DB not found:", db_path)
        return 2

    rows = load_rows(args.csv)

    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        counters: dict = {}
        for r in rows:
            upsert_row(conn, r, args.source, allow_invalid_rut=args.allow_invalid_rut, counters=counters)
        conn.commit()
        print(
            "Imported previred:",
            counters.get("inserted", 0),
            "inserted,",
            counters.get("duplicates", 0),
            "duplicates,",
            counters.get("invalid_rut", 0),
            "invalid_rut",
        )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

