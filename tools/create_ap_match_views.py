#!/usr/bin/env python3
"""Create / refresh SQL helper views for AP↔PO matching.

This script is idempotent and safe to run multiple times. It attempts to
create the views described in ideas/matching design, gracefully skipping
pieces when source tables are absent.

Views:
  v_po_line_billed_accum_pg    -- accumulated invoiced qty/amount per PO line
  v_3way_status_po_line_ext_pg -- 3-way status (PO vs Recepción vs Factura)
  v_po_line_balances_pg        -- remaining qty/amount per PO line

Usage:
  python tools/create_ap_match_views.py [--db data/chipax_data.db]
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master "
        "WHERE type IN ('table','view') AND name=?",
        (name,),
    )
    return cur.fetchone() is not None


def create_views(conn: sqlite3.Connection) -> None:
    # Basic presence checks
    has_pol = table_exists(conn, "purchase_order_lines")
    has_inv_lines = table_exists(conn, "invoice_lines")
    # Recepciones: pueden vivir en vista v_po_line_received_accum
    # o en goods_receipt_lines; se usa LEFT JOIN tolerante.

    # v_po_line_billed_accum_pg
    if has_inv_lines:
        conn.execute("DROP VIEW IF EXISTS v_po_line_billed_accum_pg")
        conn.execute(
            """
            CREATE VIEW v_po_line_billed_accum_pg AS
            SELECT il.po_line_id AS po_line_id,
                   SUM(il.qty)            AS qty_invoiced,
                   SUM(il.qty * il.unit_price) AS amt_invoiced
            FROM invoice_lines il
            WHERE il.po_line_id IS NOT NULL
            GROUP BY il.po_line_id
            """
        )

    # v_3way_status_po_line_ext_pg (only if PO lines exist)
    if has_pol:
        conn.execute("DROP VIEW IF EXISTS v_3way_status_po_line_ext_pg")
        # We allow missing billed/received views by LEFT JOIN.
        conn.execute(
            """
CREATE VIEW v_3way_status_po_line_ext_pg AS
SELECT
    pol.po_line_id,
    pol.po_id,
    pol.qty AS po_qty,
    pol.unit_price AS po_unit_price,
    COALESCE(rec.qty_received_accum,0) AS recv_qty,
    COALESCE(bill.qty_invoiced,0) AS inv_qty,
    CASE
        WHEN COALESCE(bill.qty_invoiced,0) <=
                 COALESCE(rec.qty_received_accum,0)
         AND COALESCE(rec.qty_received_accum,0) <= pol.qty
         THEN 'matching'
        WHEN COALESCE(bill.qty_invoiced,0) >
                 COALESCE(rec.qty_received_accum,0)
         THEN 'invoice_over_receipt'
        WHEN COALESCE(rec.qty_received_accum,0) > pol.qty
         THEN 'over_received'
        ELSE 'under_received'
    END AS match_status
FROM purchase_order_lines pol
LEFT JOIN v_po_line_received_accum rec
    ON rec.po_line_id = pol.po_line_id
LEFT JOIN v_po_line_billed_accum_pg bill
    ON bill.po_line_id = pol.po_line_id
            """
        )

    # v_po_line_balances_pg (remaining qty/amount)
    if has_pol:
        conn.execute("DROP VIEW IF EXISTS v_po_line_balances_pg")
        conn.execute(
            """
            CREATE VIEW v_po_line_balances_pg AS
            WITH billed AS (
              SELECT il.po_line_id,
                     SUM(il.qty) AS qty_invoiced,
                     SUM(il.qty * il.unit_price) AS amt_invoiced
              FROM invoice_lines il
              WHERE il.po_line_id IS NOT NULL
              GROUP BY il.po_line_id
            ), recv AS (
              SELECT r.po_line_id,
                     SUM(r.qty_received_accum) AS qty_received
              FROM v_po_line_received_accum r
              GROUP BY r.po_line_id
            )
            SELECT pol.po_line_id,
                   pol.po_id,
                   pol.qty AS po_qty,
                   COALESCE(recv.qty_received,0) AS qty_received,
                   COALESCE(billed.qty_invoiced,0) AS qty_invoiced,
                   (pol.qty - COALESCE(billed.qty_invoiced,0))
                       AS qty_remaining,
                   (pol.qty * pol.unit_price) AS amt_po,
                         COALESCE(billed.amt_invoiced,0) AS amt_invoiced,
                         ((pol.qty * pol.unit_price) - COALESCE(
                             billed.amt_invoiced,0)) AS amt_remaining
            FROM purchase_order_lines pol
            LEFT JOIN billed ON billed.po_line_id = pol.po_line_id
            LEFT JOIN recv   ON recv.po_line_id   = pol.po_line_id
            """
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/chipax_data.db")
    args = parser.parse_args()
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[WARN] DB not found at {db_path}; continuing (views skipped)")
        return 0
    conn = sqlite3.connect(str(db_path))
    try:
        create_views(conn)
        print("[OK] Views created/refreshed")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
