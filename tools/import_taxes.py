#!/usr/bin/env python3
"""
Importa impuestos desde CSV a la tabla canónica `taxes`.

Idempotencia: se evita duplicar por combinación (periodo, tipo, fecha_presentacion).

Uso:
  python tools/import_taxes.py --csv path/to/impuestos.{csv|xlsx} \
    --db data/chipax_data.db \
    [--source SII]
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


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS taxes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          periodo TEXT,
          tipo TEXT,
          monto_debito REAL,
          monto_credito REAL,
          neto REAL,
          estado TEXT,
          fecha_presentacion TEXT,
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


def upsert_tax(conn: sqlite3.Connection, r: dict, source_default: str | None) -> None:
    cols = {c[1] for c in conn.execute("PRAGMA table_info(taxes)").fetchall()}
    periodo = r.get("Periodo") or r.get("periodo")
    tipo = r.get("Tipo") or r.get("tipo")
    debito = norm_amount(r.get("Debito") or r.get("monto_debito") or r.get("débito"))
    credito = norm_amount(r.get("Credito") or r.get("monto_credito") or r.get("crédito"))
    neto = norm_amount(r.get("Neto") or r.get("neto") or (debito - credito))
    estado = r.get("Estado") or r.get("estado")
    fecha_presentacion = r.get("FechaPresentacion") or r.get("fecha_presentacion")
    fuente = r.get("Fuente") or r.get("fuente") or source_default or "import"

    # Detección por combinación
    cur = conn.execute(
        "SELECT 1 FROM taxes WHERE periodo = ? AND tipo = ? AND IFNULL(fecha_presentacion,'') = IFNULL(?, '')",
        (periodo, tipo, fecha_presentacion),
    )
    if cur.fetchone():
        return

    insert_cols, insert_vals, insert_params = [], [], []

    def add(col, val):
        if col in cols:
            insert_cols.append(col)
            insert_vals.append("?")
            insert_params.append(val)

    for col, val in [
        ("periodo", periodo),
        ("tipo", tipo),
        ("monto_debito", debito),
        ("monto_credito", credito),
        ("neto", neto),
        ("estado", estado),
        ("fecha_presentacion", fecha_presentacion),
        ("fuente", fuente),
    ]:
        add(col, val)

    sql = "INSERT INTO taxes (" + ", ".join(insert_cols) + ") VALUES (" + ", ".join(insert_vals) + ")"
    conn.execute(sql, insert_params)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--db", default=default_db_path(prefer_root=False))
    ap.add_argument("--source", default="import")
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print("DB not found:", db_path)
        return 2

    rows = load_rows(args.csv)

    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        n = 0
        for r in rows:
            upsert_tax(conn, r, args.source)
            n += 1
        conn.commit()
        print(f"Imported {n} tax rows (skipped duplicates)")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())


