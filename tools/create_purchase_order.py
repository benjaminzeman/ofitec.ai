#!/usr/bin/env python3
"""
Create a new Purchase Order header in the canonical DB with Ofitec sequential number.

Usage:
  python tools/create_purchase_order.py \
    --vendor-rut 76262345-9 \
    --vendor-name "Proveedor S.A." \
    --total 123456.78 [--date 2025-09-13] [--currency CLP] [--status approved] \
    [--project-name "OBRA X"] [--project-id Z001] \
    [--manual-number PO-TEST-001] \
    [--seq-prefix PO-] [--seq-padding 5] [--seq-start 1]

Notes:
- By default, generates the number from the Ofitec sequence 'po_number'.
- If --manual-number is provided and the sequence allows manual override, it will use it.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import date
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent))
from common_db import default_db_path
from rut_utils import normalize_rut, is_valid_rut
from numbering import ensure_sequence, next_number


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=default_db_path(prefer_root=False))
    ap.add_argument("--vendor-rut", required=True)
    ap.add_argument("--vendor-name", default="")
    ap.add_argument("--total", type=float, required=True)
    ap.add_argument("--date", dest="po_date", default=str(date.today()))
    ap.add_argument("--currency", default="CLP")
    ap.add_argument("--status", default="approved")
    ap.add_argument("--project-name")
    ap.add_argument("--project-id")
    ap.add_argument("--manual-number")
    ap.add_argument("--seq-prefix", default="PO-")
    ap.add_argument("--seq-padding", type=int, default=5)
    ap.add_argument("--seq-start", type=int, default=0)
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print("DB not found:", db_path)
        return 2

    vendor_rut = normalize_rut(args.vendor_rut)
    if not (vendor_rut and is_valid_rut(vendor_rut)):
        print("Invalid vendor RUT:", args.vendor_rut)
        return 2

    conn = sqlite3.connect(db_path)
    try:
        # Prepare sequence
        ensure_sequence(
            conn,
            "po_number",
            prefix=args.seq_prefix,
            padding=args.seq_padding,
            start=args.seq_start if args.seq_start and args.seq_start > 0 else None,
        )

        # Decide number
        po_number = args.manual_number or next_number(conn, "po_number")

        cols = {r[1] for r in conn.execute("PRAGMA table_info(purchase_orders_unified)").fetchall()}
        parts, vals = [], []
        def add(col, val):
            if col in cols:
                parts.append(col); vals.append(val)

        add("vendor_rut", vendor_rut)
        add("zoho_vendor_name", args.vendor_name)
        add("po_number", po_number)
        add("po_date", args.po_date)
        add("total_amount", float(args.total))
        add("currency", args.currency)
        add("status", args.status)
        add("zoho_project_name", args.project_name)
        if args.project_id:
            add("zoho_project_id", str(args.project_id))
        add("source_platform", "ofitec_manual")

        sql = (
            "INSERT INTO purchase_orders_unified (" + ", ".join(parts) + ") VALUES (" + ", ".join(["?"]*len(parts)) + ")"
        )
        conn.execute(sql, vals)
        conn.commit()
        print("Created PO:", po_number)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

