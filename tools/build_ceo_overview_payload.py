#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera JSON para /api/ceo/overview desde data/chipax_data.db
Uso (PowerShell):
    pwsh.exe -NoProfile -Command \
        "python tools/build_ceo_overview_payload.py \
            --db data/chipax_data.db \
            --out data/ceo_overview.json"
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sqlite3
from pathlib import Path


def _q(cur: sqlite3.Cursor, sql: str, params: tuple = ()):
    cur.execute(sql, params)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _scalar(cur: sqlite3.Cursor, sql: str, params: tuple = ()):  # type: ignore
    cur.execute(sql, params)
    r = cur.fetchone()
    return (r[0] if r else None)


def build_payload(db_path: str) -> dict:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Cash hoy (saldo por cuenta si existe; si no, 0)
    cash_today = 0.0
    try:
        rows = _q(
            cur,
            """
                SELECT bank_name, account_number, MAX(date(fecha)) AS last_date
                FROM bank_movements
                GROUP BY bank_name, account_number
            """,
        )
        for r in rows:
            bank = r.get('bank_name')
            acc = r.get('account_number')
            last = r.get('last_date')
            if not last:
                continue
            cur.execute(
                """
                    SELECT saldo
                    FROM bank_movements
                    WHERE bank_name IS ?
                      AND account_number IS ?
                      AND date(fecha)=?
                    ORDER BY datetime(fecha) DESC, rowid DESC
                    LIMIT 1
                """,
                (bank, acc, last),
            )
            row = cur.fetchone()
            if row and row[0] is not None:
                cash_today += float(row[0] or 0)
    except Exception:
        cash_today = 0.0
    cash = {
        "today": cash_today or 0.0,
        "d7": None,
        "d30": None,
        "d60": None,
        "d90": None,
        "shortfall_7": None,
        "shortfall_30": None,
    }

    # Revenue (ventas reales; puede estar vacío)
    try:
        month = _scalar(
            cur,
            (
                "SELECT SUM(monto_total) FROM v_facturas_venta "
                "WHERE strftime('%Y-%m', fecha)=strftime('%Y-%m','now')"
            ),
        ) or 0.0
        ytd = _scalar(
            cur,
            (
                "SELECT SUM(monto_total) FROM v_facturas_venta "
                "WHERE date(fecha)>=date(strftime('%Y-01-01','now'))"
            ),
        ) or 0.0
    except Exception:
        month = 0.0
        ytd = 0.0
    revenue = {
        "month": {"real": float(month), "plan": None, "delta_pct": None},
        "ytd": {"real": float(ytd), "plan": None, "delta_pct": None},
        "spark": [],
    }

    # Projects (salud mínima: sin presupuesto)
    try:
        proj_total = _scalar(
            cur,
            (
                "SELECT COUNT(DISTINCT project_id) FROM v_ordenes_compra "
                "WHERE project_id IS NOT NULL"
            ),
        ) or 0
    except Exception:
        try:
            proj_total = _scalar(
                cur,
                (
                    "SELECT COUNT(DISTINCT COALESCE(zoho_project_id, "
                    "zoho_project_name)) FROM purchase_orders_unified"
                ),
            ) or 0
        except Exception:
            proj_total = 0
    try:
        with_pc = _scalar(
            cur,
            "SELECT COUNT(DISTINCT project_id) FROM v_presupuesto_totales",
        ) or 0
    except Exception:
        with_pc = 0
    without_pc = max(0, int(proj_total) - int(with_pc))
    projects = {
        "total": int(proj_total or 0),
        "on_budget": None,
        "over_budget": None,
        "without_pc": int(without_pc),
        "three_way_violations": None,
        "wip_ep_to_invoice": None,
    }

    # Risk preliminar
    risk = {
        "score": 70 if without_pc > 0 else 40,
        "reasons": (
            ["Falta presupuesto en la mayoría de proyectos"]
            if without_pc > 0
            else []
        ),
    }

    alerts = []
    if without_pc > 0:
        alerts.append({
            "kind": "data_quality",
            "title": f"Falta presupuesto en {without_pc} proyectos",
            "cta": "/presupuestos/importar",
        })
    if (revenue["ytd"]["real"] or 0) == 0:
        alerts.append({
            "kind": "data_gap",
            "title": "No hay facturas de venta cargadas (AR)",
            "cta": "/ventas/importar",
        })

    actions = [
        {
            "title": "Importar presupuestos reales (XLSX)",
            "cta": "/presupuestos/importar",
        },
        {
            "title": "Importar facturas de venta desde Chipax/SII",
            "cta": "/ventas/importar",
        },
    ]

    try:
        po_total = _scalar(
            cur,
            "SELECT SUM(monto_total) FROM v_ordenes_compra",
        ) or 0.0
    except Exception:
        try:
            po_total = _scalar(
                cur,
                "SELECT SUM(total_amount) FROM purchase_orders_unified",
            ) or 0.0
        except Exception:
            po_total = 0.0

    diagnostics = {
        "db_path": str(Path(db_path).resolve()),
        "has_sales_invoices": bool(
            _scalar(cur, "SELECT COUNT(*) FROM v_facturas_venta") or 0
        ),
        "has_budgets": bool(
            _scalar(cur, "SELECT COUNT(*) FROM v_presupuesto_totales") or 0
        ),
        "po_total": float(po_total or 0),
    }

    payload = {
        "generated_at": _dt.datetime.utcnow().isoformat() + "Z",
        "cash": cash,
        "revenue": revenue,
        "margin": {
            "month_pct": None,
            "plan_pct": None,
            "delta_pp": None,
            "top_projects": [],
        },
        "working_cap": {
            "dso": None,
            "dpo": None,
            "dio": None,
            "ccc": None,
            "ar": {"d1_30": 0, "d31_60": 0, "d60_plus": 0},
            "ap": {"d7": 0, "d14": 0, "d30": 0},
        },
        "backlog": {
            "total": None,
            "cobertura_meses": None,
            "pipeline_weighted": None,
            "pipeline_vs_goal_pct": None,
        },
        "projects": projects,
        "risk": risk,
        "alerts": alerts,
        "actions": actions,
        "diagnostics": diagnostics,
    }
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='data/chipax_data.db')
    ap.add_argument('--out', default='data/ceo_overview.json')
    args = ap.parse_args()

    payload = build_payload(args.db)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(f"Wrote {out_path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
