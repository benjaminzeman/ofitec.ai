#!/usr/bin/env python3
"""
Importa facturas de venta (AR) desde un CSV exportado de Chipax a la
tabla canónica sales_invoices.

Uso:
    python tools/import_chipax_ar.py --csv path/to/chipax_ventas.csv \
        [--db data/chipax_data.db]

El mapeo de columnas esperadas se define en el documento ideas/ventas.
El script es idempotente por (rut, folio, fecha, total).
"""
from __future__ import annotations

import argparse
import csv
import os
import sqlite3
from pathlib import Path

import sys
if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent))
from common_db import default_db_path, ensure_parent_dir
from etl_common import parse_number


def normalize_amount(val: str | float | int | None) -> float:
    return round(parse_number(val), 2)


def ensure_sales_invoices(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sales_invoices (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          customer_rut TEXT,
          customer_name TEXT,
          invoice_number TEXT,
          invoice_date TEXT,
          due_date TEXT,
          currency TEXT DEFAULT 'CLP',
          net_amount REAL,
          tax_amount REAL,
          exempt_amount REAL,
          total_amount REAL,
          status TEXT,
          project_id INTEGER,
          source_platform TEXT,
          source_id TEXT,
          created_at TEXT DEFAULT (datetime('now'))
        );
                CREATE UNIQUE INDEX IF NOT EXISTS ux_sales_unique
                                ON sales_invoices(
                                    customer_rut,
                                    invoice_number,
                                    invoice_date,
                                    source_platform
                                );
        """
    )


def import_csv(csv_path: str, db_path: str) -> dict[str, int]:
    ensure_parent_dir(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_sales_invoices(conn)
        inserted = 0
        updated = 0
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rut = (row.get("RUT") or row.get("Rut") or row.get("rut") or "").strip()
                name = (""
                    or row.get("Razón Social")
                    or row.get("Razon Social")
                    or row.get("Cliente")
                    or ""
                ).strip()
                folio = (row.get("Folio") or row.get("folio") or row.get("Num") or "").strip()
                issue = (""
                    or row.get("Fecha Emisión")
                    or row.get("Fecha Emision")
                    or row.get("Emision")
                    or row.get("Fecha")
                    or ""
                ).strip()
                if not folio or not issue:
                    continue
                due = (row.get("Fecha Vencimiento") or row.get("Vencimiento") or "").strip()
                currency = (row.get("Moneda") or row.get("Moneda / TC") or "CLP").strip() or "CLP"
                net = normalize_amount(
                    row.get("Monto Neto (CLP)")
                    or row.get("Neto")
                    or row.get("Monto Neto")
                )
                exm = normalize_amount(
                    row.get("Monto Exento (CLP)")
                    or row.get("Exento")
                    or row.get("Monto Exento")
                )
                tax = normalize_amount(
                    row.get("Monto IVA (CLP)")
                    or row.get("IVA")
                    or row.get("Monto IVA")
                )
                total = normalize_amount(
                    row.get("Monto Total (CLP)")
                    or row.get("Total")
                    or row.get("Monto Total")
                )
                status = (row.get("Estado") or row.get("Status") or "open").strip().lower() or "open"
                source_id = (row.get("ID") or row.get("SourceID") or "").strip() or None

                exists = conn.execute(
                    """
                    SELECT id FROM sales_invoices
                     WHERE customer_rut=? AND invoice_number=? AND invoice_date=? AND source_platform='CHIPAX'
                    """,
                    (rut, folio, issue),
                ).fetchone()

                conn.execute(
                    """
                    INSERT INTO sales_invoices (
                        customer_rut, customer_name, invoice_number, invoice_date,
                        due_date, currency, net_amount, tax_amount, exempt_amount,
                        total_amount, status, project_id, source_platform, source_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(customer_rut, invoice_number, invoice_date, source_platform)
                    DO UPDATE SET
                        customer_name=excluded.customer_name,
                        due_date=excluded.due_date,
                        currency=excluded.currency,
                        net_amount=excluded.net_amount,
                        tax_amount=excluded.tax_amount,
                        exempt_amount=excluded.exempt_amount,
                        total_amount=excluded.total_amount,
                        status=excluded.status,
                        source_id=COALESCE(excluded.source_id, sales_invoices.source_id)
                    """,
                    (
                        rut,
                        name,
                        folio,
                        issue,
                        due,
                        currency,
                        net,
                        tax,
                        exm,
                        total,
                        status,
                        None,
                        'CHIPAX',
                        source_id,
                    ),
                )
                if exists:
                    updated += 1
                else:
                    inserted += 1
        conn.commit()
        return {"inserted": inserted, "updated": updated}
    finally:
        conn.close()




def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--csv", required=True, help="Ruta al CSV exportado desde Chipax"
    )
    ap.add_argument(
        "--db",
        default=os.environ.get("DB_PATH", default_db_path(False)),
    )
    args = ap.parse_args()

    csv_path = os.path.abspath(args.csv)
    if not os.path.exists(csv_path):
        print("CSV no encontrado:", csv_path)
        return 2
    db_path = os.path.abspath(args.db)

    metrics = import_csv(csv_path, db_path)
    print("Import AR -> sales_invoices:", metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
