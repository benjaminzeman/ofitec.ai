#!/usr/bin/env python3
"""
Apply canonical schema and views to a SQLite database without requiring the sqlite3 CLI.

Usage:
  python tools/apply_schema.py \
      --db ofitec.ai/data/chipax_data.db \
      --schema ofitec.ai/tools/schema.sql

Defaults:
  --db defaults to ofitec.ai/data/chipax_data.db (DB_PATH overrides)
  --schema defaults to ./schema.sql (alongside this script)
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
import sys
if __package__ in (None, ""):
    # Permitir ejecución directa como script
    sys.path.append(str(Path(__file__).resolve().parent))
from common_db import default_db_path, ensure_parent_dir


def main() -> int:
    here = Path(__file__).resolve().parent
    repo_root = here.parents[1]

    # Preferir chipax_data.db en el raíz del workspace para alinear docs
    default_db = default_db_path(prefer_root=False)
    default_schema = str(here / "schema.sql")

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=os.environ.get("DB_PATH", default_db), help="Path to SQLite DB")
    ap.add_argument("--schema", default=default_schema, help="Path to schema SQL file")
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    schema_path = os.path.abspath(args.schema)

    if not os.path.exists(schema_path):
        print("Schema file not found:", schema_path)
        return 2

    ensure_parent_dir(db_path)

    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Ejecutar de forma resiliente: statements individuales para tolerar
    # índices sobre columnas ausentes en instalaciones previas.
    statements = [s.strip() for s in sql.split(";") if s.strip()]

    conn = sqlite3.connect(db_path)
    try:
        for stmt in statements:
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError as e:
                msg = str(e)
                # Tolerar errores de índice cuando la columna no existe aún
                up = stmt.upper()
                if "no such column" in msg and up.startswith("CREATE") and " INDEX " in (" " + up + " "):
                    print("WARN: skipping index due to missing column:")
                    print("  ", stmt[:120].replace("\n", " ") + ("..." if len(stmt) > 120 else ""))
                    continue
                # Reintentar como script en caso de bloque multi-línea (poco probable)
                try:
                    conn.executescript(stmt)
                except Exception:
                    raise
        conn.commit()
    finally:
        conn.close()

    print("Schema applied to:", db_path)
    print("From schema:", schema_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
