#!/usr/bin/env python3
"""
Apply Ofitec projects/budgets schema (from ideas/ofitec_schema.sql) into SQLite (data/chipax_data.db).

It converts a subset of PostgreSQL DDL to SQLite-compatible DDL:
- SERIAL -> INTEGER
- DECIMAL(...) -> REAL
- DATE -> TEXT (ISO date)
- CREATE OR REPLACE VIEW -> DROP VIEW IF EXISTS + CREATE VIEW
- References are kept but SQLite will accept without enforcement unless PRAGMA foreign_keys=ON (not enabled here).
"""
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
import sys

if __package__ in (None, ""):
    here = Path(__file__).resolve().parent
    sys.path.append(str(here))

from common_db import default_db_path


def to_sqlite(sql: str) -> list[str]:
    # Normalize line endings
    sql = sql.replace("\r\n", "\n").replace("\r", "\n")
    # Strip single-line comments starting with --
    cleaned_lines = []
    for line in sql.split("\n"):
        # Remove inline comment parts
        if "--" in line:
            line = line.split("--", 1)[0]
        if line.strip() == "":
            continue
        cleaned_lines.append(line)
    sql = "\n".join(cleaned_lines)
    # Basic type replacements
    sql = re.sub(r"\bSERIAL\b", "INTEGER", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bDECIMAL\s*\([^)]*\)", "REAL", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bNUMERIC\s*\([^)]*\)", "REAL", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bDATE\b", "TEXT", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bTIMESTAMP\b", "TEXT", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bJSONB\b", "TEXT", sql, flags=re.IGNORECASE)
    sql = re.sub(r"DEFAULT\s+NOW\(\)", "DEFAULT (datetime('now'))", sql, flags=re.IGNORECASE)
    sql = re.sub(r"LEAST\(([^,]+),\s*([^\)]+)\)", r"min(\1, \2)", sql, flags=re.IGNORECASE)
    # Views: split and handle OR REPLACE
    stmts: list[str] = []
    buf: list[str] = []
    for line in sql.split("\n"):
        buf.append(line)
        if ";" in line:
            chunk = "\n".join(buf).strip()
            buf = []
            if not chunk:
                continue
            if re.search(r"CREATE\s+OR\s+REPLACE\s+VIEW", chunk, flags=re.IGNORECASE):
                m = re.search(r"CREATE\s+OR\s+REPLACE\s+VIEW\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+AS\s", chunk, flags=re.IGNORECASE)
                view_name = m.group(1) if m else None
                body = re.sub(r"CREATE\s+OR\s+REPLACE\s+VIEW\s+", "CREATE VIEW ", chunk, flags=re.IGNORECASE)
                if view_name:
                    stmts.append(f"DROP VIEW IF EXISTS {view_name}")
                stmts.append(body)
            else:
                stmts.append(chunk)
    return [s.strip() for s in stmts if s.strip()]


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    ddl_path = project_root / "ideas" / "ofitec_schema.sql"
    if not ddl_path.exists():
        print("DDL not found:", ddl_path)
        return 2
    db_path = os.environ.get("DB_PATH", default_db_path(prefer_root=False))
    with open(ddl_path, "r", encoding="utf-8") as f:
        sql = f.read()
    stmts = to_sqlite(sql)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        for s in stmts:
            try:
                cur.execute(s)
            except sqlite3.Error as e:
                # Print and continue to be resilient
                print("WARN:", e, "on", s[:120].replace("\n"," ")+ ("..." if len(s)>120 else ""))
        conn.commit()
        print("Applied Ofitec schema to:", db_path)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
