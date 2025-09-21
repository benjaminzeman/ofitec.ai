#!/usr/bin/env python3
"""
Reconciliation helpers: suggest matches across canonical views.

Source contexts supported:
- bank: v_cartola_bancaria row (amount/date/ref)
- purchase: v_facturas_compra row
- sales: v_facturas_venta row
- expense: v_gastos row
- payroll: v_sueldos row
- taxes: v_impuestos row

Scoring:
- +70 exact amount match; +50 within tolerance
- +20 same date; +10 within days window
- +10 reference/doc number fuzzy hit

Returns list of suggestions sorted by score.
"""

from __future__ import annotations

import sqlite3
import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class Source:
    kind: str
    amount: float
    date: str
    currency: str | None = None
    reference: str | None = None


def _parse_date(s: str | None) -> dt.date | None:
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s).date()
    except Exception:
        try:
            return dt.datetime.strptime(s, "%Y-%m-%d").date()
        except Exception:
            return None


def suggest_matches(
    conn: sqlite3.Connection,
    source: Source,
    *,
    amount_tol: float = 0.01,
    days_window: int = 5,
    include: Tuple[str, ...] = ("purchase", "sales", "expense", "tax", "payroll"),
) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []
    src_date = _parse_date(source.date)

    def score_row(row_date: str | None, row_amount: float, docref: str | None) -> int:
        s = 0
        # amount
        a_src = abs(source.amount or 0)
        a_row = abs(row_amount or 0)
        if abs(a_row - a_src) <= amount_tol:
            s += 70
        else:
            # within 1% tolerance of the amount if bigger values
            if a_src:
                if abs(a_row - a_src) / a_src <= 0.01:
                    s += 50
        # date
        rd = _parse_date(row_date)
        if rd and src_date:
            if rd == src_date:
                s += 20
            else:
                delta = abs((rd - src_date).days)
                if delta <= days_window:
                    s += 10
        # reference
        if source.reference and docref and source.reference.replace(" ", "") in docref.replace(" ", ""):
            s += 10
        return s

    # Queries for each target
    targets: List[Tuple[str, str, str]] = []
    if "purchase" in include:
        targets.append(
            (
                "purchase",
                "v_facturas_compra",
                "SELECT documento_numero as doc, fecha, monto_total as amount, moneda FROM v_facturas_compra",
            )
        )
    if "sales" in include:
        targets.append(
            (
                "sales",
                "v_facturas_venta",
                "SELECT documento_numero as doc, fecha, monto_total as amount, moneda FROM v_facturas_venta",
            )
        )
    if "expense" in include:
        targets.append(
            (
                "expense",
                "v_gastos",
                "SELECT gasto_id as doc, fecha, monto as amount, moneda FROM v_gastos",
            )
        )
    if "tax" in include:
        targets.append(
            (
                "tax",
                "v_impuestos",
                "SELECT periodo as doc, fecha_presentacion as fecha, neto as amount, NULL as moneda FROM v_impuestos",
            )
        )
    if "payroll" in include:
        targets.append(
            (
                "payroll",
                "v_sueldos",
                "SELECT periodo as doc, fecha_pago as fecha, liquido as amount, NULL as moneda FROM v_sueldos",
            )
        )

    for kind, view, sql in targets:
        try:
            cur = conn.execute(sql)
            for doc, fecha, amount, moneda in cur.fetchall():
                sc = score_row(fecha, float(amount or 0), str(doc) if doc is not None else None)
                if sc > 0:
                    suggestions.append(
                        {
                            "target_kind": kind,
                            "view": view,
                            "doc": doc,
                            "fecha": fecha,
                            "amount": float(amount or 0),
                            "currency": moneda,
                            "score": sc,
                        }
                    )
        except sqlite3.Error:
            # ignore missing views
            pass

    suggestions.sort(key=lambda x: x["score"], reverse=True)
    return suggestions
