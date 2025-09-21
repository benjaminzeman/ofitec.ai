#!/usr/bin/env python3
"""
Importa Proveedores desde CSV/XLSX de Zoho a la tabla canónica vendors_unified.

Uso:
  python tools/import_zoho_vendors.py --csv data/raw/zoho/Proveedores.{csv|xlsx} \
    --db data/chipax_data.db --source ZOHO

Reglas:
- No se pierde información: se preservan columnas en memoria; sólo se
  insertan campos canónicos mínimos.
- Idempotencia: UNIQUE por rut_clean evita duplicados; se puede actualizar nombre.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent))

from io_utils import load_rows
from rut_utils import normalize_rut
from common_db import default_db_path


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vendors_unified (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rut_clean TEXT UNIQUE NOT NULL,
            name_normalized TEXT NOT NULL,
            source_platform TEXT NOT NULL,
            zoho_vendor_name TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_vendor_rut ON vendors_unified(rut_clean)"
    )


def norm_name(name: str | None) -> str:
    if not name:
        return ""
    try:
        import unicodedata
        n = unicodedata.normalize("NFKD", name)
        n = "".join(ch for ch in n if not unicodedata.combining(ch))
        return n.strip()
    except Exception:
        return name.strip()


def extract_rut(row: dict) -> str:
    candidates = [
        "RUT", "rut", "R.U.T.", "RUT Proveedor", "Rut Proveedor",
        "Tax ID", "TaxID", "CF.RUT"
    ]
    for k in candidates:
        if k in row and row[k]:
            r = normalize_rut(row[k])
            if r:
                return r
    return ""


def extract_name(row: dict) -> str:
    candidates = [
        "Vendor Name", "Company Name", "Nombre", "Proveedor", "Name"
    ]
    for k in candidates:
        if k in row and row[k]:
            return str(row[k]).strip()
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__file__)
    ap.add_argument("--csv", required=True, help="Archivo CSV o XLSX de Proveedores")
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
        inserted = updated = skipped = 0
        for r in rows:
            rut = extract_rut(r)
            name = extract_name(r)
            if not rut or not name:
                skipped += 1
                continue
            name_norm = norm_name(name)
            cur = conn.execute("SELECT name_normalized FROM vendors_unified WHERE rut_clean = ?", (rut,))
            row = cur.fetchone()
            if row:
                if row[0] != name_norm:
                    conn.execute(
                        "UPDATE vendors_unified SET name_normalized = ?, zoho_vendor_name = ?, source_platform = ? WHERE rut_clean = ?",
                        (name_norm, name, args.source, rut),
                    )
                    updated += 1
                else:
                    skipped += 1
            else:
                conn.execute(
                    "INSERT INTO vendors_unified (rut_clean, name_normalized, source_platform, zoho_vendor_name) VALUES (?, ?, ?, ?)",
                    (rut, name_norm, args.source, name),
                )
                inserted += 1
        conn.commit()
        print(f"Vendors -> inserted: {inserted}, updated: {updated}, skipped: {skipped}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

