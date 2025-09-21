#!/usr/bin/env python3
"""
Importa facturas de venta desde CSV a sales_invoices (+ opcional líneas).

Idempotencia por dte_id cuando esté disponible; si no, por combinación
(customer_rut, invoice_number, invoice_date, total_amount).

Uso:
  python tools/import_sales_invoices.py --csv path/to/ventas.csv \
    --db ofitec.ai/data/chipax_data.db --batch BATCH_001 \
    [--refresh-lines] [--update-header]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
from pathlib import Path
import sys
if __package__ in (None, ""):
    _here = Path(__file__).resolve().parent
    sys.path.append(str(_here))         # tools/future
    sys.path.append(str(_here.parent))  # tools
from common_db import default_db_path


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def ensure_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "sales_invoices"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sales_invoices (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              customer_rut TEXT,
              customer_name TEXT,
              invoice_number TEXT,
              invoice_date TEXT,
              total_amount REAL,
              currency TEXT,
              status TEXT,
              source_platform TEXT,
              dte_id TEXT,
              project_id INTEGER,
              created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
    if not table_exists(conn, "sales_invoice_lines"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sales_invoice_lines (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              invoice_id INTEGER NOT NULL,
              item_name TEXT,
              item_desc TEXT,
              quantity REAL,
              unit_price REAL,
              line_total REAL,
              currency TEXT,
              tax_percent REAL,
              tax_amount REAL,
              uom TEXT,
              status TEXT
            );
            """
        )


def norm_number(v) -> float:
    try:
        if v is None or v == "":
            return 0.0
        return float(str(v).replace("$", "").replace(" ", "").replace(".", "").replace(",", "."))
    except Exception:
        try:
            return float(v)
        except Exception:
            return 0.0


def upsert_invoice(conn: sqlite3.Connection, r: dict, update_header: bool = False) -> int:
    cols = {c[1] for c in conn.execute("PRAGMA table_info(sales_invoices)").fetchall()}
    cust_rut = r.get("RUT") or r.get("customer_rut") or ""
    cust_name = r.get("Cliente") or r.get("customer_name") or ""
    inv_num = r.get("Folio") or r.get("invoice_number") or ""
    inv_date = r.get("Fecha") or r.get("invoice_date") or ""
    total = norm_number(r.get("Total") or r.get("total_amount") or 0)
    currency = r.get("Moneda") or r.get("currency") or "CLP"
    status = r.get("Estado") or r.get("status") or "issued"
    dte_id = r.get("DTE_ID") or r.get("dte_id")

    if "dte_id" in cols and dte_id:
        cur = conn.execute("SELECT rowid FROM sales_invoices WHERE dte_id = ?", (dte_id,))
        one = cur.fetchone()
        if one:
            inv_id = int(one[0])
            if update_header:
                parts, params = [], []
                if "customer_rut" in cols: parts += ["customer_rut = ?"]; params += [cust_rut]
                if "customer_name" in cols: parts += ["customer_name = ?"]; params += [cust_name]
                if "invoice_number" in cols: parts += ["invoice_number = ?"]; params += [inv_num]
                if "invoice_date" in cols: parts += ["invoice_date = ?"]; params += [inv_date]
                if "total_amount" in cols: parts += ["total_amount = ?"]; params += [total]
                if "currency" in cols: parts += ["currency = ?"]; params += [currency]
                if "status" in cols: parts += ["status = ?"]; params += [status]
                if parts:
                    conn.execute("UPDATE sales_invoices SET " + ", ".join(parts) + " WHERE rowid = ?", [*params, inv_id])
            return inv_id

    where_parts, where_params = [], []
    for k, col, val in [
        ("customer_rut", "customer_rut", cust_rut),
        ("invoice_number", "invoice_number", inv_num),
        ("invoice_date", "invoice_date", inv_date),
        ("total_amount", "total_amount", total),
    ]:
        if col in cols:
            where_parts.append(f"{col} = ?")
            where_params.append(val)
    if where_parts:
        cur = conn.execute(
            "SELECT rowid FROM sales_invoices WHERE " + " AND ".join(where_parts),
            where_params,
        )
        one = cur.fetchone()
        if one:
            inv_id = int(one[0])
            if update_header:
                parts, params = [], []
                if "currency" in cols: parts += ["currency = ?"]; params += [currency]
                if "status" in cols: parts += ["status = ?"]; params += [status]
                if "customer_name" in cols: parts += ["customer_name = ?"]; params += [cust_name]
                if parts:
                    conn.execute("UPDATE sales_invoices SET " + ", ".join(parts) + " WHERE rowid = ?", [*params, inv_id])
            return inv_id

    insert_cols, insert_vals, insert_params = [], [], []
    def add(col, val):
        insert_cols.append(col); insert_vals.append("?"); insert_params.append(val)

    for col, val in [
        ("customer_rut", cust_rut),
        ("customer_name", cust_name),
        ("invoice_number", inv_num),
        ("invoice_date", inv_date),
        ("total_amount", total),
        ("currency", currency),
        ("status", status),
        ("source_platform", r.get("source") or "import"),
        ("dte_id", dte_id),
    ]:
        if col in cols: add(col, val)

    sql = "INSERT INTO sales_invoices (" + ", ".join(insert_cols) + ") VALUES (" + ", ".join(insert_vals) + ")"
    cur = conn.execute(sql, insert_params)
    return int(cur.lastrowid)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    repo_root = Path(__file__).resolve().parents[1]
    ap.add_argument("--csv", required=True)
    ap.add_argument("--db", default=default_db_path(prefer_root=False))
    ap.add_argument("--batch", default="BATCH_SALES")
    ap.add_argument("--update-header", action="store_true")
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print("DB not found:", db_path); return 2

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_tables(conn)
        with open(args.csv, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        count = 0
        for r in rows:
            _ = upsert_invoice(conn, r, update_header=args.update_header)
            count += 1
        conn.commit()
        print(f"Imported {count} sales invoices (header-only). Use lines importer if needed.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
