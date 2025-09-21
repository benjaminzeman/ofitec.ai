#!/usr/bin/env python3
"""
List SQLite views in the canonical DB and optionally preview some rows.

Usage:
    python list_db_views.py \
        --db "ofitec.ai/data/chipax_data.db" [--sample 3]
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
import sys
if __package__ in (None, ""):
    _here = Path(__file__).resolve().parent
    sys.path.append(str(_here))         # tools/dev
    sys.path.append(str(_here.parent))  # tools
from common_db import default_db_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        dest="db_path",
        default=default_db_path(prefer_root=False),
        help="Path to SQLite DB",
    )
    parser.add_argument(
        "--sample", type=int, default=0, help="Preview N rows per known view"
    )
    args = parser.parse_args()

    db_path = os.path.abspath(args.db_path)
    if not os.path.exists(db_path):
        print("DB not found:", db_path)
        return 2

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
        )
        views = [r[0] for r in cur.fetchall()]
        print("Views (", len(views), ") in", db_path)
        for v in views:
            print(" -", v)

        if args.sample > 0:
            print("\nSamples:")
            for v in [
                "v_facturas_compra",
                "v_facturas_venta",
                "v_gastos",
                "v_impuestos",
                "v_previred",
                "v_sueldos",
                "v_cartola_bancaria",
            ]:
                if v in views:
                    print(f"\n{v} (up to {args.sample} rows):")
                    try:
                        cur = conn.execute(
                            f"SELECT * FROM {v} LIMIT ?", (args.sample,)
                        )
                        cols = [d[0] for d in cur.description]
                        print("  Columns:", ", ".join(cols))
                        for row in cur.fetchall():
                            print("  ", row)
                    except sqlite3.Error as e:
                        print("  Error reading view:", e)

    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
