#!/usr/bin/env python3
"""
Quality report for the canonical DB (data integrity, duplicates, RUTs, dates).

Checks (when tables exist):
- purchase_orders_unified: nulls (vendor_rut/po_number/po_date/total_amount), invalid RUTs,
  future dates, duplicates on (vendor_rut, po_number, po_date, total_amount), missing project name.
- vendors_unified: duplicates on rut_clean, invalid RUTs, null names.
- expenses: invalid RUTs, future dates, duplicates (comprobante OR combo), null/zero amounts.
- taxes: duplicates (periodo,tipo,fecha_presentacion), neto consistency.
- previred_contributions: invalid RUTs, duplicates combo, future dates.
- payroll_slips: invalid RUTs, duplicates combo, future dates.
- bank_movements: duplicates on external_id, null criticals.

Usage:
  python tools/quality_report.py [--db data/chipax_data.db]
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sqlite3
from pathlib import Path
import sys

if __package__ in (None, ""):
    _here = Path(__file__).resolve().parent
    sys.path.append(str(_here))
from common_db import default_db_path
from rut_utils import normalize_rut, is_valid_rut


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def parse_date(s: str | None) -> dt.date | None:
    if not s:
        return None
    try:
        # tolerate full datetime too
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        return None


def count(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> int:
    cur = conn.execute(sql, params)
    row = cur.fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def pct(part: int, whole: int) -> float:
    return 0.0 if whole <= 0 else (100.0 * part / whole)


def report_purchase_orders(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "purchase_orders_unified"):
        return
    print("\n[Purchase Orders]")
    total = count(conn, "SELECT COUNT(1) FROM purchase_orders_unified")
    nn_vendor = count(conn, "SELECT COUNT(1) FROM purchase_orders_unified WHERE vendor_rut IS NULL OR TRIM(vendor_rut) = ''")
    nn_number = count(conn, "SELECT COUNT(1) FROM purchase_orders_unified WHERE po_number IS NULL OR TRIM(po_number) = ''")
    nn_date = count(conn, "SELECT COUNT(1) FROM purchase_orders_unified WHERE po_date IS NULL OR TRIM(po_date) = ''")
    nn_amount = count(conn, "SELECT COUNT(1) FROM purchase_orders_unified WHERE total_amount IS NULL OR total_amount < 0")

    print(f" total={total}")
    print(f" null_vendor={nn_vendor} ({pct(nn_vendor, total):.1f}%)")
    print(f" null_po_number={nn_number} ({pct(nn_number, total):.1f}%)")
    print(f" null_po_date={nn_date} ({pct(nn_date, total):.1f}%)")
    print(f" invalid_amount={nn_amount} ({pct(nn_amount, total):.1f}%)")

    # invalid RUTs (pull a sample)
    cur = conn.execute("SELECT vendor_rut FROM purchase_orders_unified WHERE vendor_rut IS NOT NULL AND TRIM(vendor_rut) <> ''")
    invalid = 0
    for (rut,) in cur.fetchall():
        n = normalize_rut(rut)
        if not (n and is_valid_rut(n)):
            invalid += 1
    print(f" invalid_rut={invalid} ({pct(invalid, total):.1f}%)")

    # future dates
    cur = conn.execute("SELECT po_date FROM purchase_orders_unified WHERE po_date IS NOT NULL AND TRIM(po_date) <> ''")
    future = 0
    today = dt.date.today()
    for (s,) in cur.fetchall():
        d = parse_date(s)
        if d and d > today:
            future += 1
    print(f" future_dates={future} ({pct(future, total):.1f}%)")

    # missing project name
    if count(conn, "SELECT COUNT(1) FROM sqlite_master WHERE type='table' AND name='purchase_orders_unified'"):
        miss_proj = count(
            conn,
            "SELECT COUNT(1) FROM purchase_orders_unified WHERE zoho_project_name IS NULL OR TRIM(zoho_project_name) = ''",
        )
        print(f" missing_project_name={miss_proj} ({pct(miss_proj, total):.1f}%)")

    # duplicates combo
    cur = conn.execute(
        """
        SELECT COUNT(1) FROM (
          SELECT vendor_rut, po_number, po_date, total_amount, COUNT(*) c
          FROM purchase_orders_unified
          GROUP BY vendor_rut, po_number, po_date, total_amount
          HAVING c > 1
        ) AS d
        """
    )
    dup = int(cur.fetchone()[0])
    print(f" duplicates_keys={dup}")


def report_vendors(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "vendors_unified"):
        return
    print("\n[Vendors]")
    total = count(conn, "SELECT COUNT(1) FROM vendors_unified")
    nn_name = count(conn, "SELECT COUNT(1) FROM vendors_unified WHERE name_normalized IS NULL OR TRIM(name_normalized) = ''")
    # invalid RUTs
    cur = conn.execute("SELECT rut_clean FROM vendors_unified WHERE rut_clean IS NOT NULL AND TRIM(rut_clean) <> ''")
    invalid = 0
    for (rut,) in cur.fetchall():
        n = normalize_rut(rut)
        if not (n and is_valid_rut(n)):
            invalid += 1
    # duplicates on rut_clean
    cur = conn.execute(
        "SELECT COUNT(1) FROM (SELECT rut_clean, COUNT(*) c FROM vendors_unified GROUP BY rut_clean HAVING c > 1)"
    )
    dup = int(cur.fetchone()[0])
    print(f" total={total} null_name={nn_name} invalid_rut={invalid} duplicates_rut={dup}")


def report_expenses(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "expenses"):
        return
    print("\n[Expenses]")
    total = count(conn, "SELECT COUNT(1) FROM expenses")
    nn_amount = count(conn, "SELECT COUNT(1) FROM expenses WHERE monto IS NULL OR monto < 0")
    # invalid RUTs
    cur = conn.execute("SELECT proveedor_rut FROM expenses WHERE proveedor_rut IS NOT NULL AND TRIM(proveedor_rut) <> ''")
    invalid = 0
    for (rut,) in cur.fetchall():
        n = normalize_rut(rut)
        if not (n and is_valid_rut(n)):
            invalid += 1
    # future dates
    cur = conn.execute("SELECT fecha FROM expenses WHERE fecha IS NOT NULL AND TRIM(fecha) <> ''")
    future = 0
    today = dt.date.today()
    for (s,) in cur.fetchall():
        d = parse_date(s)
        if d and d > today:
            future += 1
    # duplicates via comprobante or combo
    dup_comp = count(conn, "SELECT COUNT(1) FROM (SELECT comprobante, COUNT(*) c FROM expenses WHERE comprobante IS NOT NULL AND TRIM(comprobante) <> '' GROUP BY comprobante HAVING c > 1)")
    dup_combo = count(
        conn,
        "SELECT COUNT(1) FROM (SELECT fecha, monto, proveedor_rut, descripcion, COUNT(*) c FROM expenses GROUP BY fecha, monto, proveedor_rut, descripcion HAVING c > 1)",
    )
    print(
        f" total={total} invalid_amount={nn_amount} invalid_rut={invalid} future_dates={future} duplicates_comprobante={dup_comp} duplicates_combo={dup_combo}"
    )


def report_taxes(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "taxes"):
        return
    print("\n[Taxes]")
    total = count(conn, "SELECT COUNT(1) FROM taxes")
    dup = count(
        conn,
        "SELECT COUNT(1) FROM (SELECT periodo, tipo, IFNULL(fecha_presentacion,'') f, COUNT(*) c FROM taxes GROUP BY periodo, tipo, f HAVING c > 1)",
    )
    # neto consistency
    inconsistent = count(
        conn,
        "SELECT COUNT(1) FROM taxes WHERE neto IS NOT NULL AND (ABS(neto - (COALESCE(monto_debito,0) - COALESCE(monto_credito,0))) > 0.01)",
    )
    print(f" total={total} duplicates_keys={dup} neto_inconsistent={inconsistent}")


def report_previred(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "previred_contributions"):
        return
    print("\n[Previred]")
    total = count(conn, "SELECT COUNT(1) FROM previred_contributions")
    # invalid RUTs
    invalid = 0
    for row in conn.execute(
        "SELECT rut_trabajador, rut_empresa FROM previred_contributions WHERE (rut_trabajador IS NOT NULL AND TRIM(rut_trabajador) <> '') OR (rut_empresa IS NOT NULL AND TRIM(rut_empresa) <> '')"
    ):
        for rut in row:
            if rut:
                n = normalize_rut(rut)
                if not (n and is_valid_rut(n)):
                    invalid += 1
    # future dates
    future = 0
    today = dt.date.today()
    for (s,) in conn.execute(
        "SELECT fecha_pago FROM previred_contributions WHERE fecha_pago IS NOT NULL AND TRIM(fecha_pago) <> ''"
    ):
        d = parse_date(s)
        if d and d > today:
            future += 1
    # duplicates combo
    dup = count(
        conn,
        "SELECT COUNT(1) FROM (SELECT periodo, IFNULL(rut_trabajador,''), IFNULL(rut_empresa,''), IFNULL(fecha_pago,''), IFNULL(monto_total,0), COUNT(*) c FROM previred_contributions GROUP BY 1,2,3,4,5 HAVING c>1)",
    )
    print(f" total={total} invalid_rut={invalid} future_dates={future} duplicates_keys={dup}")


def report_payroll(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "payroll_slips"):
        return
    print("\n[Payroll]")
    total = count(conn, "SELECT COUNT(1) FROM payroll_slips")
    # invalid RUTs
    invalid = 0
    for (rut,) in conn.execute(
        "SELECT rut_trabajador FROM payroll_slips WHERE rut_trabajador IS NOT NULL AND TRIM(rut_trabajador) <> ''"
    ):
        n = normalize_rut(rut)
        if not (n and is_valid_rut(n)):
            invalid += 1
    # future dates
    future = 0
    today = dt.date.today()
    for (s,) in conn.execute(
        "SELECT fecha_pago FROM payroll_slips WHERE fecha_pago IS NOT NULL AND TRIM(fecha_pago) <> ''"
    ):
        d = parse_date(s)
        if d and d > today:
            future += 1
    # duplicates combo
    dup = count(
        conn,
        "SELECT COUNT(1) FROM (SELECT periodo, IFNULL(rut_trabajador,''), IFNULL(fecha_pago,''), IFNULL(bruto,0), IFNULL(liquido,0), COUNT(*) c FROM payroll_slips GROUP BY 1,2,3,4,5 HAVING c>1)",
    )
    print(f" total={total} invalid_rut={invalid} future_dates={future} duplicates_keys={dup}")


def report_bank_movements(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "bank_movements"):
        return
    print("\n[Bank Movements]")
    total = count(conn, "SELECT COUNT(1) FROM bank_movements")
    # duplicates by external_id
    dup = count(
        conn,
        "SELECT COUNT(1) FROM (SELECT external_id, COUNT(*) c FROM bank_movements WHERE external_id IS NOT NULL AND TRIM(external_id) <> '' GROUP BY external_id HAVING c > 1)",
    )
    nn_date = count(conn, "SELECT COUNT(1) FROM bank_movements WHERE fecha IS NULL OR TRIM(fecha) = ''")
    nn_amount = count(conn, "SELECT COUNT(1) FROM bank_movements WHERE monto IS NULL")
    print(f" total={total} duplicates_external_id={dup} null_fecha={nn_date} null_monto={nn_amount}")


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
        print("Quality report for:", db_path)
        report_purchase_orders(conn)
        report_vendors(conn)
        report_expenses(conn)
        report_taxes(conn)
        report_previred(conn)
        report_payroll(conn)
        report_bank_movements(conn)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


