#!/usr/bin/env python3
"""
Create or refresh canonical Finance views in chipax_data.db.

Views created:
 - v_facturas_compra (proxy from purchase_orders_unified if available)
 - v_facturas_venta (proxy from sales_invoices if available)
 - v_gastos (placeholder or from expenses)
 - v_impuestos (placeholder or from taxes)
 - v_previred (placeholder or from previred_contributions)
 - v_sueldos (placeholder or from payroll_slips)
 - v_cartola_bancaria (placeholder or from bank_movements)
 - v_ar_payments (sum of conciliations for AR)
 - v_sales_invoices_with_project (AR enriched with paid_amount)

Usage:
    python create_finance_views.py --db "ofitec.ai/data/chipax_data.db"

Idempotent: existing views are dropped and recreated.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from typing import List, Tuple
from pathlib import Path
import sys
if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent))
from common_db import default_db_path, ensure_parent_dir


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    )
    return cur.fetchone() is not None


def view_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='view' AND name=?", (name,)
    )
    return cur.fetchone() is not None


def drop_view(conn: sqlite3.Connection, name: str) -> None:
    if view_exists(conn, name):
        conn.execute(f"DROP VIEW IF EXISTS {name}")


def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    try:
        cur = conn.execute(f"PRAGMA table_info({table})")
        return [str(r[1]) for r in cur.fetchall()]
    except sqlite3.Error:
        return []


def create_views(conn: sqlite3.Connection) -> List[Tuple[str, str]]:
    """Create or refresh all finance views; returns list of (view, status)."""
    statuses: List[Tuple[str, str]] = []

    # 1) v_facturas_compra
    drop_view(conn, "v_facturas_compra")
    if table_exists(conn, "purchase_orders_unified"):
        conn.execute(
            """
            CREATE VIEW v_facturas_compra AS
            SELECT
              po_number         AS documento_numero,
              po_date           AS fecha,
              vendor_rut        AS proveedor_rut,
              zoho_vendor_name  AS proveedor_nombre,
              total_amount      AS monto_total,
              COALESCE(currency, 'CLP') AS moneda,
              COALESCE(status, 'unknown') AS estado,
              COALESCE(source_platform, 'unknown') AS fuente
            FROM purchase_orders_unified;
            """
        )
        statuses.append(
            (
                "v_facturas_compra",
                "created_from_purchase_orders_unified",
            )
        )
    else:
        # Fallback placeholder (no rows)
        conn.execute(
            """
            CREATE VIEW v_facturas_compra AS
            SELECT
              CAST(NULL AS TEXT) AS documento_numero,
              CAST(NULL AS TEXT) AS fecha,
              CAST(NULL AS TEXT) AS proveedor_rut,
              CAST(NULL AS TEXT) AS proveedor_nombre,
              CAST(NULL AS REAL) AS monto_total,
              CAST(NULL AS TEXT) AS moneda,
              CAST(NULL AS TEXT) AS estado,
              CAST(NULL AS TEXT) AS fuente
            WHERE 1=0;
            """
        )
        statuses.append(
            (
                "v_facturas_compra",
                "placeholder_created_table_missing",
            )
        )

    # Helper to create empty placeholder view with defined columns
    def create_placeholder(view: str, columns: List[Tuple[str, str]]):
        drop_view(conn, view)
        select_list = ",\n              ".join(
            [f"CAST(NULL AS {typ}) AS {name}" for name, typ in columns]
        )
        sql = f"""
            CREATE VIEW {view} AS
            SELECT
              {select_list}
            WHERE 1=0;
        """
        conn.execute(sql)
        statuses.append((view, "placeholder_created"))

    # 2) v_facturas_venta
    drop_view(conn, "v_facturas_venta")
    if table_exists(conn, "sales_invoices"):
        # Detect column naming (issue_date vs invoice_date) and map
        cols = set(table_columns(conn, "sales_invoices"))
        fecha_col = "issue_date" if "issue_date" in cols else "invoice_date"
        moneda_col = "currency" if "currency" in cols else None
        status_col = "status" if "status" in cols else None
        fuente_col = "source_platform" if "source_platform" in cols else None
        conn.execute(
            f"""
            CREATE VIEW v_facturas_venta AS
            SELECT
              invoice_number  AS documento_numero,
              {fecha_col}     AS fecha,
              customer_rut    AS cliente_rut,
              customer_name   AS cliente_nombre,
              total_amount    AS monto_total,
              COALESCE({moneda_col or "'CLP'"}, 'CLP') AS moneda,
              COALESCE({status_col or "'unknown'"}, 'unknown') AS estado,
              COALESCE({fuente_col or "'unknown'"}, 'unknown') AS fuente
            FROM sales_invoices;
            """
        )
        statuses.append(("v_facturas_venta", "created_from_sales_invoices"))
    else:
        create_placeholder(
            "v_facturas_venta",
            [
                ("documento_numero", "TEXT"),
                ("fecha", "TEXT"),
                ("cliente_rut", "TEXT"),
                ("cliente_nombre", "TEXT"),
                ("monto_total", "REAL"),
                ("moneda", "TEXT"),
                ("estado", "TEXT"),
                ("fuente", "TEXT"),
            ],
        )

    # 3) v_gastos
    drop_view(conn, "v_gastos")
    if table_exists(conn, "expenses"):
        conn.execute(
            """
            CREATE VIEW v_gastos AS
            SELECT
              CAST(id AS TEXT) AS gasto_id,
              fecha,
              categoria,
              descripcion,
              monto,
              COALESCE(moneda, 'CLP') AS moneda,
              proveedor_rut,
              proyecto,
              COALESCE(fuente, 'unknown') AS fuente
            FROM expenses;
            """
        )
        statuses.append(("v_gastos", "created_from_expenses"))
    else:
        create_placeholder(
            "v_gastos",
            [
                ("gasto_id", "TEXT"),
                ("fecha", "TEXT"),
                ("categoria", "TEXT"),
                ("descripcion", "TEXT"),
                ("monto", "REAL"),
                ("moneda", "TEXT"),
                ("proveedor_rut", "TEXT"),
                ("proyecto", "TEXT"),
                ("fuente", "TEXT"),
            ],
        )

    # 4) v_impuestos
    drop_view(conn, "v_impuestos")
    if table_exists(conn, "taxes"):
        conn.execute(
            """
            CREATE VIEW v_impuestos AS
            SELECT
              periodo,
              tipo,
              monto_debito,
              monto_credito,
              COALESCE(neto, monto_debito - monto_credito) AS neto,
              estado,
              fecha_presentacion,
              COALESCE(fuente, 'unknown') AS fuente
            FROM taxes;
            """
        )
        statuses.append(("v_impuestos", "created_from_taxes"))
    else:
        create_placeholder(
            "v_impuestos",
            [
                ("periodo", "TEXT"),
                ("tipo", "TEXT"),
                ("monto_debito", "REAL"),
                ("monto_credito", "REAL"),
                ("neto", "REAL"),
                ("estado", "TEXT"),
                ("fecha_presentacion", "TEXT"),
                ("fuente", "TEXT"),
            ],
        )

    # Ensure placeholders exist even if tables were present earlier
    # (idempotent safeguard)
    if not table_exists(conn, "expenses"):
        create_placeholder(
            "v_gastos",
            [
                ("gasto_id", "TEXT"),
                ("fecha", "TEXT"),
                ("categoria", "TEXT"),
                ("descripcion", "TEXT"),
                ("monto", "REAL"),
                ("moneda", "TEXT"),
                ("proveedor_rut", "TEXT"),
                ("proyecto", "TEXT"),
                ("fuente", "TEXT"),
            ],
        )
    if not table_exists(conn, "taxes"):
        create_placeholder(
            "v_impuestos",
            [
                ("periodo", "TEXT"),
                ("tipo", "TEXT"),
                ("monto_debito", "REAL"),
                ("monto_credito", "REAL"),
                ("neto", "REAL"),
                ("estado", "TEXT"),
                ("fecha_presentacion", "TEXT"),
                ("fuente", "TEXT"),
            ],
        )

    # 5) v_previred
    drop_view(conn, "v_previred")
    if table_exists(conn, "previred_contributions"):
        conn.execute(
            """
            CREATE VIEW v_previred AS
            SELECT
              periodo,
              rut_trabajador,
              nombre_trabajador,
              rut_empresa,
              monto_total,
              estado,
              fecha_pago,
              COALESCE(fuente, 'unknown') AS fuente
            FROM previred_contributions;
            """
        )
        statuses.append(("v_previred", "created_from_previred_contributions"))
    else:
        create_placeholder(
            "v_previred",
            [
                ("periodo", "TEXT"),
                ("rut_trabajador", "TEXT"),
                ("nombre_trabajador", "TEXT"),
                ("rut_empresa", "TEXT"),
                ("monto_total", "REAL"),
                ("estado", "TEXT"),
                ("fecha_pago", "TEXT"),
                ("fuente", "TEXT"),
            ],
        )

    # 6) v_sueldos
    drop_view(conn, "v_sueldos")
    if table_exists(conn, "payroll_slips"):
        conn.execute(
            """
            CREATE VIEW v_sueldos AS
            SELECT
              periodo,
              rut_trabajador,
              nombre_trabajador,
              cargo,
              bruto,
              liquido,
              descuentos,
              fecha_pago,
              COALESCE(fuente, 'unknown') AS fuente
            FROM payroll_slips;
            """
        )
        statuses.append(("v_sueldos", "created_from_payroll_slips"))
    else:
        create_placeholder(
            "v_sueldos",
            [
                ("periodo", "TEXT"),
                ("rut_trabajador", "TEXT"),
                ("nombre_trabajador", "TEXT"),
                ("cargo", "TEXT"),
                ("bruto", "REAL"),
                ("liquido", "REAL"),
                ("descuentos", "REAL"),
                ("fecha_pago", "TEXT"),
                ("fuente", "TEXT"),
            ],
        )

    # 7) v_cartola_bancaria
    drop_view(conn, "v_cartola_bancaria")
    if table_exists(conn, "bank_movements"):
        conn.execute(
            """
            CREATE VIEW v_cartola_bancaria AS
            SELECT
              fecha,
              bank_name      AS banco,
              account_number AS cuenta,
              glosa,
              monto,
              moneda,
              tipo,
              saldo,
              referencia,
              COALESCE(fuente, 'unknown') AS fuente
            FROM bank_movements;
            """
        )
        statuses.append(("v_cartola_bancaria", "created_from_bank_movements"))
    else:
        create_placeholder(
            "v_cartola_bancaria",
            [
                ("fecha", "TEXT"),
                ("banco", "TEXT"),
                ("cuenta", "TEXT"),
                ("glosa", "TEXT"),
                ("monto", "REAL"),
                ("moneda", "TEXT"),
                ("tipo", "TEXT"),
                ("saldo", "REAL"),
                ("referencia", "TEXT"),
                ("fuente", "TEXT"),
            ],
        )

    # 8) v_ar_payments (sum of reconciled amounts for sales invoices)
    drop_view(conn, "v_ar_payments")
    if (
        table_exists(conn, "recon_links")
        and table_exists(conn, "recon_reconciliations")
    ):
        conn.execute(
            """
            CREATE VIEW v_ar_payments AS
            SELECT rl.sales_invoice_id AS invoice_id,
                   SUM(COALESCE(rl.amount,0)) AS paid_amount
            FROM recon_links rl
                                    JOIN recon_reconciliations rr
                                        ON rr.id = rl.reconciliation_id
                                     AND rr.context='sales'
            WHERE rl.sales_invoice_id IS NOT NULL
            GROUP BY rl.sales_invoice_id;
            """
        )
        statuses.append(("v_ar_payments", "created_from_recon_links"))
    else:
        conn.execute(
            """
            CREATE VIEW v_ar_payments AS
            SELECT CAST(NULL AS INTEGER) AS invoice_id,
                   CAST(NULL AS REAL)    AS paid_amount
            WHERE 1=0;
            """
        )
        statuses.append(("v_ar_payments", "placeholder_created"))

    # 9) v_sales_invoices_with_project (AR enriched)
    drop_view(conn, "v_sales_invoices_with_project")
    if table_exists(conn, "sales_invoices"):
        cols = set(table_columns(conn, "sales_invoices"))
        # Map available or fallback to NULL casts
        # helper removed to satisfy linter (was unused)

        issue_date_expr = (
            "issue_date"
            if "issue_date" in cols
            else (
                "invoice_date"
                if "invoice_date" in cols
                else "CAST(NULL AS TEXT)"
            )
        )
        due_date_expr = (
            "due_date" if "due_date" in cols else "CAST(NULL AS TEXT)"
        )
        net_expr = (
            "net_amount" if "net_amount" in cols else "CAST(NULL AS REAL)"
        )
        tax_expr = (
            "tax_amount" if "tax_amount" in cols else "CAST(NULL AS REAL)"
        )
        exm_expr = (
            "exempt_amount"
            if "exempt_amount" in cols
            else "CAST(NULL AS REAL)"
        )
        curr_expr = "currency" if "currency" in cols else "'CLP'"
        status_expr = "status" if "status" in cols else "'open'"
        src_expr = (
            "source_platform" if "source_platform" in cols else "'unknown'"
        )

        conn.execute(
            f"""
            CREATE VIEW v_sales_invoices_with_project AS
            SELECT si.id                 AS invoice_id,
                   si.customer_rut      AS customer_rut,
                   si.customer_name     AS customer_name,
                   si.invoice_number    AS invoice_number,
                   {issue_date_expr}    AS issue_date,
                   {due_date_expr}      AS due_date,
                   {curr_expr}          AS currency,
                   {net_expr}           AS net_amount,
                   {tax_expr}           AS tax_amount,
                   {exm_expr}           AS exempt_amount,
                   si.total_amount      AS total_amount,
                   COALESCE({status_expr},'open') AS status,
                   si.project_id        AS project_id,
                   COALESCE({src_expr},'unknown') AS source,
                   COALESCE(paid.paid_amount, 0) AS paid_amount,
             CASE WHEN COALESCE(paid.paid_amount,0) >=
                        COALESCE(si.total_amount,0)
                    THEN 1 ELSE 0 END AS fully_paid
            FROM sales_invoices si
            LEFT JOIN v_ar_payments paid ON paid.invoice_id = si.id;
            """
        )
        statuses.append(
            ("v_sales_invoices_with_project", "created_from_sales_invoices")
        )
    else:
        conn.execute(
            """
            CREATE VIEW v_sales_invoices_with_project AS
            SELECT CAST(NULL AS INTEGER) AS invoice_id,
                   CAST(NULL AS TEXT)    AS customer_rut,
                   CAST(NULL AS TEXT)    AS customer_name,
                   CAST(NULL AS TEXT)    AS invoice_number,
                   CAST(NULL AS TEXT)    AS issue_date,
                   CAST(NULL AS TEXT)    AS due_date,
                   CAST(NULL AS TEXT)    AS currency,
                   CAST(NULL AS REAL)    AS net_amount,
                   CAST(NULL AS REAL)    AS tax_amount,
                   CAST(NULL AS REAL)    AS exempt_amount,
                   CAST(NULL AS REAL)    AS total_amount,
                   CAST(NULL AS TEXT)    AS status,
                   CAST(NULL AS INTEGER) AS project_id,
                   CAST(NULL AS TEXT)    AS source,
                   CAST(NULL AS REAL)    AS paid_amount,
                   CAST(NULL AS INTEGER) AS fully_paid
            WHERE 1=0;
            """
        )
    statuses.append(("v_sales_invoices_with_project", "placeholder_created"))

    # 10) v_ar_aging_by_project (sum outstanding by aging buckets per project)
    drop_view(conn, "v_ar_aging_by_project")
    if table_exists(conn, "sales_invoices"):
        cols = set(table_columns(conn, "sales_invoices"))
        issue_date_expr = (
            "issue_date"
            if "issue_date" in cols
            else (
                "invoice_date"
                if "invoice_date" in cols
                else "CAST(NULL AS TEXT)"
            )
        )
        due_date_expr = (
            "due_date" if "due_date" in cols else issue_date_expr
        )
        lines = [
            "CREATE VIEW v_ar_aging_by_project AS",
            "WITH base AS (",
            "  SELECT",
            "    si.id AS invoice_id,",
            "    si.project_id AS project_id,",
            "    COALESCE(si.total_amount,0) -",
            "    COALESCE(p.paid_amount,0) AS raw_outstanding,",
            "    CASE WHEN (COALESCE(si.total_amount,0) -",
            "               COALESCE(p.paid_amount,0)) < 0 THEN 0",
            "         ELSE (COALESCE(si.total_amount,0) -",
            "               COALESCE(p.paid_amount,0)) END AS outstanding,",
            f"    CAST(julianday('now') - julianday(COALESCE({due_date_expr},",
            f"         {issue_date_expr})) AS INTEGER) AS days",
            "  FROM sales_invoices si",
            "  LEFT JOIN v_ar_payments p ON p.invoice_id = si.id",
            ")",
            "SELECT",
            "  project_id,",
            "  SUM(CASE WHEN days <= 30 THEN outstanding ELSE 0 END)",
            "    AS d0_30,",
            "  SUM(CASE WHEN days BETWEEN 31 AND 60 THEN",
            "           outstanding ELSE 0 END)",
            "    AS d31_60,",
            "  SUM(CASE WHEN days BETWEEN 61 AND 90 THEN",
            "           outstanding ELSE 0 END)",
            "    AS d61_90,",
            "  SUM(CASE WHEN days > 90 THEN outstanding ELSE 0 END) AS d90p",
            "FROM base",
            "WHERE project_id IS NOT NULL",
            "GROUP BY project_id;",
        ]
        conn.execute("\n".join(lines))
        statuses.append(
            ("v_ar_aging_by_project", "created_from_sales_invoices")
        )
    else:
        conn.execute(
            """
            CREATE VIEW v_ar_aging_by_project AS
            SELECT CAST(NULL AS INTEGER) AS project_id,
                   CAST(NULL AS REAL)    AS d0_30,
                   CAST(NULL AS REAL)    AS d31_60,
                   CAST(NULL AS REAL)    AS d61_90,
                   CAST(NULL AS REAL)    AS d90p
            WHERE 1=0;
            """
        )
        statuses.append(("v_ar_aging_by_project", "placeholder_created"))

    # 11) Useful indexes (best-effort)
    try:
        if table_exists(conn, "sales_invoices"):
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_si_invoice_date "
                "ON sales_invoices(invoice_date)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_si_customer "
                "ON sales_invoices(customer_rut)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_si_project "
                "ON sales_invoices(project_id)"
            )
        if table_exists(conn, "recon_links"):
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rl_sales "
                "ON recon_links(sales_invoice_id)"
            )
    except sqlite3.Error:
        # ignore index creation errors
        pass

    return statuses


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    # Usar chipax_data.db dentro del proyecto si no hay DB_PATH
    default_db = default_db_path(prefer_root=False)
    parser.add_argument(
        "--db",
        dest="db_path",
        default=default_db,
        help=f"Path to SQLite DB (default: {default_db})",
    )
    parser.add_argument(
        "--no-drop",
        action="store_true",
        help="Deprecated (views are dropped automatically if present)",
    )
    args = parser.parse_args()

    db_path = os.path.abspath(args.db_path)
    ensure_parent_dir(db_path)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        statuses = create_views(conn)
        conn.commit()
    finally:
        conn.close()

    print("Finance views updated in:", db_path)
    for name, status in statuses:
        print(f" - {name}: {status}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
