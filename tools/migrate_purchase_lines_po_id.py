#!/usr/bin/env python3
"""
Migración segura para alinear `purchase_lines_unified` con la columna `po_id` e índices.

Acciones:
- Añade columna `po_id INTEGER` si no existe.
- Crea índices recomendados si la columna existe:
  - ix_lines_po_id ON purchase_lines_unified(po_id)
  - ux_lines_po_zohoid ON purchase_lines_unified(po_id, zoho_line_id)

No modifica datos existentes salvo agregar la columna; no rellena `po_id` para filas antiguas.

Uso:
  python tools/migrate_purchase_lines_po_id.py --db ofitec.ai/data/chipax_data.db
"""

from __future__ import annotations

import argparse
import os
import sqlite3

from pathlib import Path
import sys

if __package__ in (None, ""):
    _here = Path(__file__).resolve().parent
    sys.path.append(str(_here))
from common_db import default_db_path


def column_exists(conn: sqlite3.Connection, table: str, col: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cur.fetchall())


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
        # 1) add column if missing
        if not column_exists(conn, "purchase_lines_unified", "po_id"):
            conn.execute("ALTER TABLE purchase_lines_unified ADD COLUMN po_id INTEGER")
            print("Added column po_id to purchase_lines_unified")
        else:
            print("Column po_id already exists")

        # 2) create indexes (idempotent)
        try:
            conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_lines_po_id ON purchase_lines_unified(po_id)"
            )
            print("Index ix_lines_po_id ensured")
        except sqlite3.Error as e:
            print("WARN: unable to create ix_lines_po_id:", e)
        try:
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_lines_po_zohoid ON purchase_lines_unified(po_id, zoho_line_id)"
            )
            print("Index ux_lines_po_zohoid ensured")
        except sqlite3.Error as e:
            print("WARN: unable to create ux_lines_po_zohoid:", e)

        # 3) report null po_id count
        try:
            cur = conn.execute(
                "SELECT COUNT(1) FROM purchase_lines_unified WHERE po_id IS NULL"
            )
            c = cur.fetchone()[0]
            print("Rows with po_id NULL:", c)
        except sqlite3.Error:
            pass

        conn.commit()
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

