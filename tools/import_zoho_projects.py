#!/usr/bin/env python3
"""
Importa Proyectos desde CSV/XLSX de Zoho a projects_analytic_map.

Uso:
  python tools/import_zoho_projects.py --csv data/raw/zoho/Proyectos.{csv|xlsx} \
    --db data/chipax_data.db --source ZOHO
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent))

from io_utils import load_rows
from common_db import default_db_path


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS projects_analytic_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zoho_project_id TEXT,
            zoho_project_name TEXT,
            analytic_code TEXT,
            slug TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(zoho_project_id)
        );
        """
    )


def slugify(name: str | None) -> str:
    if not name:
        return ""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def main() -> int:
    ap = argparse.ArgumentParser(description=__file__)
    ap.add_argument("--csv", required=True, help="Archivo CSV o XLSX de Proyectos")
    ap.add_argument("--db", default=default_db_path(prefer_root=False))
    ap.add_argument("--source", default="ZOHO")
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print("DB not found:", db_path)
        return 2

    rows = load_rows(args.csv)

    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        ins = upd = skip = 0
        for r in rows:
            pid = r.get("Project ID") or r.get("ProjectId") or r.get("ID") or ""
            pname = r.get("Project Name") or r.get("Proyecto") or r.get("Name") or ""
            if not pid and not pname:
                skip += 1
                continue
            slug = slugify(pname)
            cur = conn.execute("SELECT zoho_project_name FROM projects_analytic_map WHERE zoho_project_id = ?", (str(pid),))
            row = cur.fetchone()
            if row:
                if pname and row[0] != pname:
                    conn.execute(
                        "UPDATE projects_analytic_map SET zoho_project_name = ?, slug = ? WHERE zoho_project_id = ?",
                        (pname, slug, str(pid)),
                    )
                    upd += 1
                else:
                    skip += 1
            else:
                conn.execute(
                    "INSERT INTO projects_analytic_map (zoho_project_id, zoho_project_name, analytic_code, slug) VALUES (?, ?, ?, ?)",
                    (str(pid), pname, None, slug),
                )
                ins += 1
        conn.commit()
        print(f"Projects -> inserted: {ins}, updated: {upd}, skipped: {skip}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

