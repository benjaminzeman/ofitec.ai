#!/usr/bin/env python3
"""
Importa movimientos bancarios desde CSV a bank_movements (idempotente por external_id cuando esté).

Uso:
  python tools/import_bank_movements.py --csv path/to/movimientos.{csv|xlsx} \
    --db data/chipax_data.db --source CHIPAX
"""

from __future__ import annotations

import argparse
import csv
import os
import sqlite3
from pathlib import Path
import sys
if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent))
from common_db import default_db_path
from io_utils import load_rows
from etl_common import parse_number


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bank_movements (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          fecha TEXT,
          bank_name TEXT,
          account_number TEXT,
          glosa TEXT,
          monto REAL,
          moneda TEXT,
          tipo TEXT,
          saldo REAL,
          referencia TEXT,
          fuente TEXT,
          external_id TEXT
        );
        """
    )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_bank_external ON bank_movements(external_id)")


def norm_amount(val) -> float:
    return round(parse_number(val), 2)


def upsert_movement(conn: sqlite3.Connection, r: dict, source: str) -> None:
    cols = {c[1] for c in conn.execute("PRAGMA table_info(bank_movements)").fetchall()}
    fecha = r.get("Fecha") or r.get("fecha")
    bank = r.get("Banco") or r.get("bank") or r.get("bank_name")
    account = r.get("Cuenta") or r.get("account") or r.get("account_number")
    glosa = r.get("Glosa") or r.get("glosa") or r.get("Descripción") or r.get("description")
    amount = norm_amount(r.get("Monto") or r.get("amount"))
    moneda = r.get("Moneda") or r.get("currency") or "CLP"
    tipo = r.get("Tipo") or r.get("type") or ("credit" if amount > 0 else "debit")
    saldo = norm_amount(r.get("Saldo") or r.get("balance") or 0)
    ref = r.get("Referencia") or r.get("reference")
    external = r.get("ID") or r.get("external_id") or None

    if external:
        cur = conn.execute("SELECT 1 FROM bank_movements WHERE external_id = ?", (external,))
        if cur.fetchone():
            # Already there; could update minor fields if desired
            return

    conn.execute(
        (
            "INSERT INTO bank_movements (fecha, bank_name, account_number, glosa, monto, moneda, tipo, saldo, referencia, fuente, external_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        (fecha, bank, account, glosa, amount, moneda, tipo, saldo, ref, source, external),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    repo_root = Path(__file__).resolve().parents[1]
    ap.add_argument("--csv", required=True)
    ap.add_argument("--db", default=default_db_path(prefer_root=False))
    ap.add_argument("--source", default="import")
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print("DB not found:", db_path); return 2

    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        rows = load_rows(args.csv)
        n = 0
        for r in rows:
            upsert_movement(conn, r, source=args.source)
            n += 1
        conn.commit()
        print(f"Imported {n} bank movements")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
