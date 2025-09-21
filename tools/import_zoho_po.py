#!/usr/bin/env python3
"""
Importador básico de Órdenes de Compra desde CSV de Zoho.

- Staging todas las columnas a `zoho_po_raw`
- Normalización: cabeceras en `purchase_orders_unified` (idempotente) y líneas en `purchase_lines_unified`
- RUT normalizado (body-DV)
- Mapa analítico de proyectos en `projects_analytic_map`

Uso:
  python tools/import_zoho_po.py --csv path/to/Orden_de_compra.{csv|xlsx} --db data/chipax_data.db --batch BATCH_001 --refresh-lines --update-header
"""
from __future__ import annotations

import argparse
import csv
from io_utils import load_rows
import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path
import sys
if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent))
from common_db import default_db_path
from rut_utils import normalize_rut, is_valid_rut
from numbering import ensure_sequence, next_number


def ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS zoho_po_raw (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT,
            row_index INTEGER,
            row_json TEXT,
            import_batch_id TEXT,
            hash TEXT
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS purchase_lines_unified (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            po_id INTEGER NOT NULL,
            item_name TEXT,
            item_desc TEXT,
            quantity REAL,
            unit_price REAL,
            line_total REAL,
            currency TEXT,
            tax_percent REAL,
            tax_amount REAL,
            uom TEXT,
            status TEXT,
            zoho_line_id TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_lines_po_id ON purchase_lines_unified(po_id)"
    )
    try:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_lines_po_zohoid ON purchase_lines_unified(po_id, zoho_line_id)"
        )
    except sqlite3.Error:
        pass
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


def table_columns(conn: sqlite3.Connection, name: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({name})")
    return {r[1] for r in cur.fetchall()}


def _slugify(name: str | None) -> str:
    if not name:
        return ""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def _rut_normalize(rut: str | None) -> str:
    n = normalize_rut(rut)
    return n or ""


def _map_status(zoho_status: str | None) -> str | None:
    if not zoho_status:
        return None
    s = str(zoho_status).strip().lower()
    mapping = {
        "draft": "draft",
        "submitted": "submitted",
        "approved": "approved",
        "open": "approved",
        "cancelled": "cancelled",
        "canceled": "cancelled",
        "closed": "approved",
    }
    return mapping.get(s, s)


def _parse_number(val) -> float:
    try:
        if val is None or val == "":
            return 0.0
        return float(str(val).replace("$", "").replace(" ", "").replace(".", "").replace(",", "."))
    except Exception:
        try:
            return float(val)
        except Exception:
            return 0.0


def upsert_po(
    conn: sqlite3.Connection,
    row: dict,
    *,
    update_header: bool = False,
    number_strategy: str = "zoho",
    manual_number_col: str | None = None,
    sequence_name: str = "po_number",
) -> int:
    cols = table_columns(conn, "purchase_orders_unified")
    vendor_name = row.get("Vendor Name") or row.get("Proveedor") or ""
    vendor_rut = _rut_normalize(row.get("CF.RUT") or row.get("RUT") or "")
    src_po_number = row.get("Purchase Order Number") or row.get("OC") or ""
    manual_num = None
    if manual_number_col:
        manual_num = row.get(manual_number_col) or row.get(manual_number_col.replace(" ", "_"))
    if number_strategy == "manual" and manual_num:
        po_number = str(manual_num)
    else:
        po_number = src_po_number
    po_date = row.get("Purchase Order Date") or row.get("Fecha") or ""
    total_amount = row.get("Total") or row.get("Monto") or "0"
    currency = row.get("Currency Code") or row.get("Moneda") or "CLP"
    project = row.get("Project Name") or row.get("Proyecto") or ""
    project_id = row.get("Project ID") or row.get("ProjectId") or None
    zoho_po_id = row.get("Purchase Order ID") or row.get("PO ID")
    zoho_status = _map_status(row.get("Purchase Order Status"))
    exchange_rate = row.get("Exchange Rate") or row.get("Tipo Cambio")

    if "zoho_po_id" in cols and zoho_po_id:
        cur = conn.execute(
            "SELECT rowid FROM purchase_orders_unified WHERE zoho_po_id = ?",
            (zoho_po_id,),
        )
        found = cur.fetchone()
        if found:
            po_id = int(found[0])
            if update_header:
                parts = []
                params = []
                if "currency" in cols and currency:
                    parts.append("currency = ?"); params.append(currency)
                if "status" in cols and zoho_status:
                    parts.append("status = ?"); params.append(zoho_status)
                if "zoho_project_name" in cols and project is not None:
                    parts.append("zoho_project_name = ?"); params.append(project)
                if "zoho_project_id" in cols and project_id is not None:
                    parts.append("zoho_project_id = ?"); params.append(str(project_id))
                if "zoho_vendor_name" in cols and vendor_name:
                    parts.append("zoho_vendor_name = ?"); params.append(vendor_name)
                if "po_date" in cols and po_date:
                    parts.append("po_date = ?"); params.append(po_date)
                if "total_amount" in cols and total_amount:
                    parts.append("total_amount = ?"); params.append(_parse_number(total_amount))
                if "exchange_rate" in cols and exchange_rate:
                    parts.append("exchange_rate = ?"); params.append(_parse_number(exchange_rate))
                if parts:
                    sql = "UPDATE purchase_orders_unified SET " + ", ".join(parts) + " WHERE rowid = ?"
                    conn.execute(sql, [*params, po_id])
            return po_id

    parts = []
    params = []
    if "vendor_rut" in cols:
        parts.append("vendor_rut = ?"); params.append(vendor_rut)
    if "po_number" in cols:
        parts.append("po_number = ?"); params.append(po_number)
    if "po_date" in cols:
        parts.append("po_date = ?"); params.append(po_date)
    if "total_amount" in cols:
        parts.append("total_amount = ?"); params.append(total_amount)
    # Build a detection WHERE; if strategy is 'ofitec', ignore po_number for idempotency
    where_parts = []
    where_params: list = []
    if "vendor_rut" in cols:
        where_parts.append("vendor_rut = ?"); where_params.append(vendor_rut)
    if number_strategy != "ofitec" and "po_number" in cols:
        where_parts.append("po_number = ?"); where_params.append(po_number)
    if "po_date" in cols:
        where_parts.append("po_date = ?"); where_params.append(po_date)
    if "total_amount" in cols:
        where_parts.append("total_amount = ?"); where_params.append(total_amount)
    where = " AND ".join(where_parts)
    if where:
        cur = conn.execute(
            f"SELECT rowid FROM purchase_orders_unified WHERE {where}",
            where_params,
        )
        found = cur.fetchone()
        if found:
            po_id = int(found[0])
            if update_header:
                parts = []
                params2 = []
                if "currency" in cols and currency:
                    parts.append("currency = ?"); params2.append(currency)
                if "status" in cols and zoho_status:
                    parts.append("status = ?"); params2.append(zoho_status)
                if "zoho_project_name" in cols and project is not None:
                    parts.append("zoho_project_name = ?"); params2.append(project)
                if "zoho_project_id" in cols and project_id is not None:
                    parts.append("zoho_project_id = ?"); params2.append(str(project_id))
                if "zoho_vendor_name" in cols and vendor_name:
                    parts.append("zoho_vendor_name = ?"); params2.append(vendor_name)
                if "exchange_rate" in cols and exchange_rate:
                    parts.append("exchange_rate = ?"); params2.append(_parse_number(exchange_rate))
                if parts:
                    sql = "UPDATE purchase_orders_unified SET " + ", ".join(parts) + " WHERE rowid = ?"
                    conn.execute(sql, [*params2, po_id])
            return po_id

    # Insert new
    insert_cols = []
    insert_vals = []
    insert_params = []

    def add(col: str, value):
        insert_cols.append(col)
        insert_vals.append("?")
        insert_params.append(value)

    if "vendor_rut" in cols:
        add("vendor_rut", vendor_rut)
    if "zoho_vendor_name" in cols:
        add("zoho_vendor_name", vendor_name)
    if "po_number" in cols:
        if number_strategy == "ofitec":
            add("po_number", next_number(conn, sequence_name))
        else:
            add("po_number", po_number)
    if "po_date" in cols:
        add("po_date", po_date)
    if "total_amount" in cols:
        add("total_amount", _parse_number(total_amount))
    if "currency" in cols:
        add("currency", currency)
    if "status" in cols:
        add("status", zoho_status or "approved")
    if "zoho_project_name" in cols:
        add("zoho_project_name", project)
    if "zoho_project_id" in cols and project_id:
        add("zoho_project_id", str(project_id))
    if "zoho_po_id" in cols and zoho_po_id:
        add("zoho_po_id", zoho_po_id)
    if "exchange_rate" in cols and exchange_rate:
        add("exchange_rate", _parse_number(exchange_rate))
    if "source_platform" in cols:
        add("source_platform", "zoho_import")

    sql = (
        "INSERT INTO purchase_orders_unified (" + ", ".join(insert_cols) + ") VALUES (" + ", ".join(insert_vals) + ")"
    )
    cur = conn.execute(sql, insert_params)
    return int(cur.lastrowid)


def insert_line_for_po(conn: sqlite3.Connection, po_id: int, row: dict) -> None:
    item_name = row.get("Item Name") or row.get("Item") or row.get("Item_Name")
    item_desc = row.get("Item Desc") or row.get("Description") or row.get("Item_Desc")
    qty_raw = row.get("QuantityOrdered") or row.get("Qty") or row.get("Quantity") or "0"
    price_raw = row.get("Item Price") or row.get("Price") or "0"
    total_raw = row.get("Item Total") or row.get("Line Total")
    currency = row.get("Currency Code") or row.get("Moneda") or "CLP"
    tax_percent = row.get("Item Tax %") or row.get("Tax Percent")
    tax_amount = row.get("Item Tax Amount") or row.get("Tax Amount")
    uom = row.get("UOM") or row.get("Unit")
    status = row.get("Line Status") or None
    zoho_line_id = row.get("Line Item ID") or row.get("Item ID") or None
    try:
        quantity = float(str(qty_raw).replace(",", ".")) if qty_raw not in (None, "") else 0.0
    except Exception:
        quantity = 0.0
    try:
        unit_price = float(str(price_raw).replace(",", ".")) if price_raw not in (None, "") else 0.0
    except Exception:
        unit_price = 0.0
    try:
        if total_raw not in (None, ""):
            line_total = float(str(total_raw).replace(",", "."))
        else:
            line_total = quantity * unit_price
    except Exception:
        line_total = quantity * unit_price

    if zoho_line_id:
        cur = conn.execute(
            "SELECT 1 FROM purchase_lines_unified WHERE po_id = ? AND zoho_line_id = ?",
            (po_id, str(zoho_line_id)),
        )
        if cur.fetchone():
            return

    conn.execute(
        (
            "INSERT INTO purchase_lines_unified (po_id, item_name, item_desc, quantity, unit_price, line_total, currency, tax_percent, tax_amount, uom, status, zoho_line_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        (
            po_id,
            item_name,
            item_desc,
            quantity,
            unit_price,
            line_total,
            currency,
            float(tax_percent) if isinstance(tax_percent, (int, float)) else None,
            float(tax_amount) if isinstance(tax_amount, (int, float)) else None,
            uom,
            status,
            str(zoho_line_id) if zoho_line_id is not None else None,
        ),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    repo_root = Path(__file__).resolve().parents[1]
    ap.add_argument("--csv", required=True, help="Ruta al CSV de Zoho")
    ap.add_argument("--db", default=default_db_path(prefer_root=False))
    ap.add_argument("--batch", default="BATCH_001")
    ap.add_argument("--refresh-lines", action="store_true", help="Reemplaza líneas por OC antes de insertar (idempotente)")
    ap.add_argument("--update-header", action="store_true", help="Actualiza campos de cabecera si la OC ya existe")
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print("DB not found:", db_path)
        return 2

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_tables(conn)

        rows = load_rows(args.csv)

        # Staging
        for idx, r in enumerate(rows):
            h = hashlib.sha256(json.dumps(r, sort_keys=True).encode("utf-8")).hexdigest()
            conn.execute(
                "INSERT INTO zoho_po_raw (source_file, row_index, row_json, import_batch_id, hash) VALUES (?, ?, ?, ?, ?)",
                (os.path.basename(args.csv), idx, json.dumps(r, ensure_ascii=False), args.batch, h),
            )

        # Normalización (cabeceras + líneas)
        po_ids: dict[str, int] = {}
        cleared: set[int] = set()
        for idx, r in enumerate(rows):
            key = r.get("Purchase Order ID") or f"{r.get('CF.RUT','')}-{r.get('Purchase Order Number','')}-{r.get('Purchase Order Date','')}"
            po_id = po_ids.get(key)
            if po_id is None:
                po_id = upsert_po(conn, r, update_header=getattr(args, "update_header", False))
                po_ids[key] = po_id
                if getattr(args, "refresh_lines", False):
                    conn.execute("DELETE FROM purchase_lines_unified WHERE po_id = ?", (po_id,))
                    cleared.add(po_id)

            insert_line_for_po(conn, po_id, r)

            # Mapear proyecto analítico
            proj_id = r.get("Project ID") or r.get("ProjectId")
            proj_name = r.get("Project Name") or r.get("Proyecto")
            if proj_id or proj_name:
                slug = _slugify(proj_name)
                analytic_code = str(proj_id) if proj_id else slug
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO projects_analytic_map (zoho_project_id, zoho_project_name, analytic_code, slug) VALUES (?, ?, ?, ?)",
                        (str(proj_id) if proj_id else None, proj_name, analytic_code, slug),
                    )
                except sqlite3.Error:
                    pass

        conn.commit()
        # Conciliar total cabecera si está vacío
        for po_id in po_ids.values():
            cur = conn.execute("SELECT SUM(COALESCE(line_total,0)) FROM purchase_lines_unified WHERE po_id = ?", (po_id,))
            sum_lines = cur.fetchone()[0] or 0.0
            conn.execute(
                "UPDATE purchase_orders_unified SET total_amount = COALESCE(NULLIF(total_amount, 0), ?) WHERE rowid = ?",
                (sum_lines, po_id),
            )
        conn.commit()
        print(f"Staged {len(rows)} filas, normalizadas {len(po_ids)} cabeceras y líneas insertadas. Totales conciliados cuando correspondía.")
        return 0
    finally:
        conn.commit()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())




