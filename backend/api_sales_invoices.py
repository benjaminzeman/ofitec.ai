"""Sales invoices API endpoints for listing and summary data."""

from __future__ import annotations
# pylint: disable=too-many-locals,too-many-branches,too-many-statements

from typing import Dict

from flask import Blueprint, jsonify, request

from backend.db_utils import db_conn  # reuse unified connection helper

bp = Blueprint("sales", __name__)


@bp.get("/api/sales_invoices")
def api_sales_invoices_list():
    """Return paginated sales invoices with optional filters and ordering."""
    args = request.args
    page = max(1, int(args.get("page", 1)))
    page_size = max(1, min(200, int(args.get("page_size", 50))))
    offset = (page - 1) * page_size
    order_by = (args.get("order_by") or "fecha").lower()
    order_dir = (args.get("order_dir") or "DESC").upper()
    order_dir = "ASC" if order_dir == "ASC" else "DESC"
    allowed = {
        "fecha",
        "monto_total",
        "cliente_nombre",
        "cliente_rut",
        "documento_numero",
    }
    if order_by in allowed:
        order_sql = f" ORDER BY {order_by} {order_dir}"
    else:
        order_sql = " ORDER BY fecha DESC"

    filters: Dict[str, str] = {}
    if v := args.get("rut", type=str):
        filters["rut"] = v
    if v := args.get("moneda", type=str):
        filters["moneda"] = v
    if v := args.get("estado", type=str):
        filters["estado"] = v
    if v := args.get("date_from", type=str):
        filters["date_from"] = v
    if v := args.get("date_to", type=str):
        filters["date_to"] = v
    if v := args.get("project_id", type=str):
        filters["project_id"] = v
    if v := args.get("search", type=str):
        filters["search"] = v

    with db_conn() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type='view' AND name='v_facturas_venta'"
        )
        has_view = cur.fetchone() is not None
        if has_view:
            where = ["1=1"]
            params: list = []
            if v := filters.get("rut"):
                where.append("COALESCE(cliente_rut,'')=?")
                params.append(v)
            if v := filters.get("moneda"):
                where.append("COALESCE(moneda,'CLP')=?")
                params.append(v)
            if v := filters.get("estado"):
                where.append("COALESCE(estado,'unknown')=?")
                params.append(v)
            if v := filters.get("date_from"):
                where.append("fecha >= ?")
                params.append(v)
            if v := filters.get("date_to"):
                where.append("fecha <= ?")
                params.append(v)
            if v := filters.get("project_id"):
                cur.execute(
                    (
                        "SELECT 1 FROM sqlite_master "
                        "WHERE type='view' AND name='v_sales_invoices_"
                        "with_project'"
                    )
                )
                has_enriched = cur.fetchone() is not None
                if has_enriched:
                    base = "v_sales_invoices_with_project"
                    where.append("COALESCE(project_id, -1) = ?")
                    params.append(int(v))
                else:
                    base = "v_facturas_venta"
            else:
                base = "v_facturas_venta"
            if v := filters.get("search"):
                where.append(
                    "(COALESCE(cliente_nombre,'') LIKE ? "
                    "OR COALESCE(documento_numero,'') LIKE ?)"
                )
                like = f"%{v}%"
                params.extend([like, like])
            where_sql = " AND ".join(where)
            count_sql = f"SELECT COUNT(1) FROM {base} WHERE {where_sql}"
            data_sql = (
                f"SELECT * FROM {base} WHERE {where_sql}{order_sql} "
                f"LIMIT ? OFFSET ?"
            )
            cur.execute(count_sql, params)
            total = int(cur.fetchone()[0] or 0)
            cur.execute(data_sql, [*params, page_size, offset])
            items = [dict(r) for r in cur.fetchall()]
        else:
            items, total = _fallback_sales_invoices(cur, filters, order_sql, page_size, offset)

    return jsonify(
        {
            "items": items,
            "meta": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            },
        }
    )


def _fallback_sales_invoices(cur, filters: Dict[str, str], order_sql: str, page_size: int, offset: int):
    """Return (items,total) using dynamic column introspection when view is absent.

    Keeps logic isolated so main endpoint stays readable.
    """
    # Ensure table exists (minimal schema) to avoid errors on empty DB.
    cur.execute(
        "CREATE TABLE IF NOT EXISTS sales_invoices("
        " id INTEGER PRIMARY KEY,"
        " invoice_number TEXT,"
        " invoice_date TEXT,"
        " customer_rut TEXT,"
        " customer_name TEXT,"
        " total_amount REAL,"
        " currency TEXT,"
        " status TEXT,"
        " source_platform TEXT)"
    )
    where = ["1=1"]
    params: list = []
    cur.execute("PRAGMA table_info(sales_invoices)")
    cols = {row[1] for row in cur.fetchall()}
    flags = {c: (c in cols) for c in [
        "invoice_number", "invoice_date", "customer_rut", "customer_name", "total_amount", "currency", "status", "source_platform"
    ]}
    # Filters (guard by column presence when needed)
    if (v := filters.get("rut")) and flags["customer_rut"]:
        where.append("COALESCE(customer_rut,'')=?")
        params.append(v)
    if (v := filters.get("moneda")) and flags["currency"]:
        where.append("COALESCE(currency,'CLP')=?")
        params.append(v)
    if (v := filters.get("estado")) and flags["status"]:
        where.append("COALESCE(status,'unknown')=?")
        params.append(v)
    if v := filters.get("date_from"):
        where.append("invoice_date >= ?")
        params.append(v)
    if v := filters.get("date_to"):
        where.append("invoice_date <= ?")
        params.append(v)
    if v := filters.get("search"):
        cond_parts = []
        if flags["customer_name"]:
            cond_parts.append("COALESCE(customer_name,'') LIKE ?")
        cond_parts.append("COALESCE(invoice_number,'') LIKE ?")
        where.append("(" + " OR ".join(cond_parts) + ")")
        like = f"%{v}%"
        if flags["customer_name"]:
            params.append(like)
        params.append(like)
    where_sql = " AND ".join(where)
    count_sql = f"SELECT COUNT(1) FROM sales_invoices WHERE {where_sql}"
    select_parts = [
        ("invoice_number AS documento_numero" if flags["invoice_number"] else "NULL AS documento_numero"),
        ("invoice_date AS fecha" if flags["invoice_date"] else "NULL AS fecha"),
        ("customer_rut AS cliente_rut" if flags["customer_rut"] else "NULL AS cliente_rut"),
        ("customer_name AS cliente_nombre" if flags["customer_name"] else "NULL AS cliente_nombre"),
        ("total_amount AS monto_total" if flags["total_amount"] else "0 AS monto_total"),
        ("COALESCE(currency,'CLP') AS moneda" if flags["currency"] else "'CLP' AS moneda"),
        ("COALESCE(status,'unknown') AS estado" if flags["status"] else "'unknown' AS estado"),
        ("COALESCE(source_platform,'unknown') AS fuente" if flags["source_platform"] else "'unknown' AS fuente"),
    ]
    # If ordering by fecha but column missing, fallback
    ord_sql = order_sql
    if not flags["invoice_date"] and "fecha" in order_sql:
        ord_sql = " ORDER BY id DESC"
    data_sql = (
        "SELECT " + ", ".join(select_parts) + f" FROM sales_invoices WHERE {where_sql}{ord_sql} LIMIT ? OFFSET ?"
    )
    cur.execute(count_sql, params)
    total = int(cur.fetchone()[0] or 0)
    cur.execute(data_sql, [*params, page_size, offset])
    items = [dict(r) for r in cur.fetchall()]
    return items, total


@bp.get("/api/ar_aging_by_project")
def api_ar_aging_by_project():
    """Expose AR aging view grouped by project when the view exists."""
    with db_conn() as con:
        cur = con.cursor()
        cur.execute(
            (
                "SELECT 1 FROM sqlite_master WHERE type='view' "
                "AND name='v_ar_aging_by_project'"
            )
        )
        if cur.fetchone() is None:
            return jsonify({"items": []})
        cur.execute(
            (
                "SELECT project_id, d0_30, d31_60, d61_90, d90p "
                "FROM v_ar_aging_by_project ORDER BY project_id"
            )
        )
        items = [
            {
                "project_id": int(r[0]) if r[0] is not None else None,
                "d0_30": float(r[1] or 0),
                "d31_60": float(r[2] or 0),
                "d61_90": float(r[3] or 0),
                "d90p": float(r[4] or 0),
            }
            for r in cur.fetchall()
        ]
    return jsonify({"items": items})
