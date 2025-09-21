#!/usr/bin/env python3
"""
Introspección rápida de la BD canónica `chipax_data.db`.

Muestra:
- Ruta y tamaño del archivo
- Listado de tablas y vistas (con conteo de filas para tablas)
- Top-N tablas por cantidad de filas
- (Opcional) Vista previa de una tabla o vista

Uso:
  python tools/introspect_chipax.py [--db PATH] [--top 10] [--preview TABLE_OR_VIEW]

Respeta `DB_PATH` si está definido. Por defecto usa el raíz del workspace.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
from typing import List, Tuple

import sys
if __package__ in (None, ""):
    _here = Path(__file__).resolve().parent
    sys.path.append(str(_here))         # tools/dev
    sys.path.append(str(_here.parent))  # tools
from common_db import default_db_path, existing_db_path


def human_size(p: Path) -> str:
    n = p.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def list_tables(conn: sqlite3.Connection) -> List[str]:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [r[0] for r in cur.fetchall()]


def list_views(conn: sqlite3.Connection) -> List[str]:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
    return [r[0] for r in cur.fetchall()]


def count_rows(conn: sqlite3.Connection, name: str) -> int:
    try:
        cur = conn.execute(f"SELECT COUNT(1) FROM {name}")
        return int(cur.fetchone()[0])
    except Exception:
        return -1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=default_db_path(prefer_root=False), help="Ruta a la BD")
    ap.add_argument("--top", type=int, default=10, help="Top-N tablas por filas")
    ap.add_argument("--preview", help="Nombre de tabla o vista a previsualizar (hasta 10 filas)")
    args = ap.parse_args()

    # Elegir path existente si posible, sino respetar el proporcionado
    db_path = existing_db_path() or os.path.abspath(args.db)

    if not os.path.exists(db_path):
        print("DB not found:", db_path)
        return 2

    p = Path(db_path)
    print("DB:", p)
    try:
        print("Size:", human_size(p))
    except Exception:
        pass

    conn = sqlite3.connect(db_path)
    try:
        tables = list_tables(conn)
        views = list_views(conn)
        print("Tables (", len(tables), ")")
        for t in tables:
            c = count_rows(conn, t)
            print(f" - {t:32s} rows={c if c >= 0 else 'n/a'}")
        print("Views (", len(views), ")")
        for v in views:
            print(f" - {v}")

        # Top-N tablas por filas
        tc: List[Tuple[str, int]] = []
        for t in tables:
            c = count_rows(conn, t)
            if c >= 0:
                tc.append((t, c))
        tc.sort(key=lambda x: x[1], reverse=True)
        print("\nTop", args.top, "tables by row count:")
        for name, cnt in tc[: args.top]:
            print(f" - {name}: {cnt}")

        if args.preview:
            name = args.preview
            print(f"\nPreview {name} (up to 10 rows):")
            try:
                cur = conn.execute(f"SELECT * FROM {name} LIMIT 10")
                cols = [d[0] for d in cur.description]
                print("  Columns:", ", ".join(cols))
                for row in cur.fetchall():
                    print("  ", row)
            except sqlite3.Error as e:
                print("  Error:", e)

    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
