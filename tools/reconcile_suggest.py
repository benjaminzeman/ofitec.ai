#!/usr/bin/env python3
"""
Suggest reconciliation candidates across canonical views from a given source.

Usage examples:
- From bank movement values:
  python tools/reconcile_suggest.py --source bank --amount 125000 --date 2025-02-12 --ref OC-123 \
    [--db data/chipax_data.db] [--days 5] [--amount-tol 0.01]

- From a purchase order header (by id):
  python tools/reconcile_suggest.py --source purchase --id 42
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
import sys

if __package__ in (None, ""):
    _here = Path(__file__).resolve().parent
    sys.path.append(str(_here))
from common_db import default_db_path
from reconcile_utils import Source, suggest_matches


def fetch_source_from_id(conn: sqlite3.Connection, kind: str, row_id: int) -> Source:
    if kind == "bank":
        cur = conn.execute(
            "SELECT monto, fecha, referencia, moneda FROM bank_movements WHERE id = ?",
            (row_id,),
        )
        r = cur.fetchone()
        if not r:
            raise SystemExit("bank_movements id not found")
        return Source(kind="bank", amount=float(r[0] or 0), date=r[1] or "", reference=r[2] or None, currency=r[3] or None)
    if kind == "purchase":
        cur = conn.execute(
            "SELECT total_amount, po_date, po_number, currency FROM purchase_orders_unified WHERE id = ?",
            (row_id,),
        )
        r = cur.fetchone()
        if not r:
            raise SystemExit("purchase_orders_unified id not found")
        return Source(kind="purchase", amount=float(r[0] or 0), date=r[1] or "", reference=r[2] or None, currency=r[3] or None)
    if kind == "sales":
        cur = conn.execute(
            "SELECT total_amount, invoice_date, invoice_number, currency FROM sales_invoices WHERE id = ?",
            (row_id,),
        )
        r = cur.fetchone()
        if not r:
            raise SystemExit("sales_invoices id not found")
        return Source(kind="sales", amount=float(r[0] or 0), date=r[1] or "", reference=r[2] or None, currency=r[3] or None)
    if kind == "expense":
        cur = conn.execute(
            "SELECT monto, fecha, comprobante, moneda FROM expenses WHERE id = ?",
            (row_id,),
        )
        r = cur.fetchone()
        if not r:
            raise SystemExit("expenses id not found")
        return Source(kind="expense", amount=float(r[0] or 0), date=r[1] or "", reference=r[2] or None, currency=r[3] or None)
    raise SystemExit(f"unsupported kind for --id: {kind}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=default_db_path(prefer_root=False))
    ap.add_argument("--source", choices=["bank", "purchase", "sales", "expense"], required=True)
    ap.add_argument("--id", type=int, help="Row id from the corresponding table (bank_movements.id, purchase_orders_unified.id, ...)")
    ap.add_argument("--amount", type=float)
    ap.add_argument("--date")
    ap.add_argument("--ref")
    ap.add_argument("--currency", default="CLP")
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--amount-tol", type=float, default=0.01)
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print("DB not found:", db_path)
        return 2

    conn = sqlite3.connect(db_path)
    try:
        if args.id:
            src = fetch_source_from_id(conn, args.source, args.id)
        else:
            if args.amount is None or not args.date:
                print("When not using --id, --amount and --date are required")
                return 2
            src = Source(kind=args.source, amount=args.amount, date=args.date, currency=args.currency, reference=args.ref)

        suggestions = suggest_matches(
            conn,
            src,
            amount_tol=args.__dict__["amount_tol"],
            days_window=args.days,
        )
        print("Source:", src)
        print("Suggestions (top 10):")
        for s in suggestions[:10]:
            print(" -", s)

    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


