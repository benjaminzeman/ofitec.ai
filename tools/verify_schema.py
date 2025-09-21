#!/usr/bin/env python3
"""
Verifica que la DB actual cumpla con el esquema mínimo (tablas y vistas clave).
Imprime faltantes y discrepancias básicas.

Uso:
  python tools/verify_schema.py --db ofitec.ai/data/chipax_data.db
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
import sys
if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent))
from common_db import default_db_path


REQUIRED_TABLES = [
    "purchase_orders_unified",
    "purchase_lines_unified",
    "vendors_unified",
    "bank_movements",
]

REQUIRED_VIEWS = [
    "v_facturas_compra",
    "v_facturas_venta",
    "v_cartola_bancaria",
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=default_db_path(prefer_root=False))
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print("DB not found:", db_path)
        return 2

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table','view')")
        items = cur.fetchall()
        tables = {n for (n, t) in items if t == "table"}
        views = {n for (n, t) in items if t == "view"}

        ok = True
        for t in REQUIRED_TABLES:
            if t not in tables:
                print("Missing table:", t)
                ok = False
        for v in REQUIRED_VIEWS:
            if v not in views:
                print("Missing view:", v)
                ok = False

        if ok:
            print("Schema OK — required tables/views present")
            return 0
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
