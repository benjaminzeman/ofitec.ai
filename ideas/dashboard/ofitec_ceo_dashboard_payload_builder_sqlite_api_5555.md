# OFITEC — **CEO Dashboard Payload Builder** (SQLite + API 5555)
> Genera un **payload real** para `/api/ceo/overview` leyendo tu `data/chipax_data.db`. Incluye script Python, consultas SQL y *fallbacks* cuando falten vistas/datos. Apto para SQLite; fácil de portar a Postgres.

---

## 1) Qué entrega el payload
- `cash` (hoy; horizonte reservado para futura proyección)
- `revenue` (mes/YTD desde `v_facturas_venta`)
- `projects` (conteos por salud; hoy: proyectos con PO y **sin PC**)
- `risk` (score preliminar si falta presupuesto)
- `alerts`/`actions` (brechas de datos clave)
- `diagnostics` (para entender por qué algo sale vacío)

> **Nota**: Con tu ZIP actual, `v_facturas_venta` está vacía (0 ventas), `v_presupuesto_totales` está vacío (0 presupuestos), `v_ordenes_compra` tiene **4.564** OCs por **$5.040.424.868**. El payload refleja esa realidad.

---

## 2) Script — `tools/build_ceo_overview_payload.py`
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera JSON para /api/ceo/overview desde data/chipax_data.db
Uso:
  python tools/build_ceo_overview_payload.py --db data/chipax_data.db --out data/ceo_overview.json
"""
import argparse, sqlite3, json, datetime

def q(cur, sql, params=()):
    cur.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]

def scalar(cur, sql, params=()):
    cur.execute(sql, params)
    r = cur.fetchone()
    return (list(r)[0] if r else None)

def build_payload(db_path:str):
    con = sqlite3.connect(db_path); con.row_factory = sqlite3.Row
    cur = con.cursor()

    # --- CASH (saldo hoy por cuenta si existe; si no, 0) ---
    cash_today = 0.0
    rows = q(cur, """
      SELECT bank_name, account_number, MAX(date(fecha)) AS last_date
      FROM bank_movements GROUP BY bank_name, account_number
    """)
    for r in rows:
        bank, acc, last = r['bank_name'], r['account_number'], r['last_date']
        if last is None: continue
        cur.execute("""
          SELECT saldo FROM bank_movements
          WHERE bank_name IS ? AND account_number IS ? AND date(fecha)=?
          ORDER BY datetime(fecha) DESC, id DESC LIMIT 1
        """, (bank, acc, last))
        row = cur.fetchone()
        if row and row['saldo'] is not None:
            cash_today += float(row['saldo'] or 0)
    cash = {"today": cash_today or 0.0, "d7": None, "d30": None, "d60": None, "d90": None,
            "shortfall_7": None, "shortfall_30": None}

    # --- REVENUE (ventas reales; hoy vacío en tu DB) ---
    month = scalar(cur, "SELECT SUM(monto_total) FROM v_facturas_venta WHERE strftime('%Y-%m', fecha)=strftime('%Y-%m','now')") or 0.0
    ytd   = scalar(cur, "SELECT SUM(monto_total) FROM v_facturas_venta WHERE date(fecha)>=date(strftime('%Y-01-01','now'))") or 0.0
    revenue = {"month": {"real": month, "plan": None, "delta_pct": None},
               "ytd":   {"real": ytd,   "plan": None, "delta_pct": None},
               "spark": []}

    # --- PROJECTS (salud mínima: sin presupuesto) ---
    proj_total = scalar(cur, "SELECT COUNT(DISTINCT project_id) FROM v_ordenes_compra WHERE project_id IS NOT NULL") or 0
    with_pc    = scalar(cur, "SELECT COUNT(DISTINCT project_id) FROM v_presupuesto_totales") or 0
    without_pc = max(0, proj_total - with_pc)
    projects = {"total": int(proj_total), "on_budget": None, "over_budget": None,
                "without_pc": int(without_pc), "three_way_violations": None, "wip_ep_to_invoice": None}

    # --- RISK (preliminar) ---
    risk = {"score": 70 if without_pc>0 else 40,
            "reasons": (["Falta presupuesto en la mayoría de proyectos"] if without_pc>0 else [])}

    # --- ALERTS/ACTIONS ---
    alerts = []
    if without_pc>0:
        alerts.append({"kind":"data_quality","title":f"Falta presupuesto en {without_pc} proyectos","cta":"/presupuestos/importar"})
    if (ytd or 0)==0:
        alerts.append({"kind":"data_gap","title":"No hay facturas de venta cargadas (AR)","cta":"/ventas/importar"})
    actions = [
        {"title":"Importar presupuestos reales (XLSX)","cta":"/presupuestos/importar"},
        {"title":"Importar facturas de venta desde Chipax/SII","cta":"/ventas/importar"}
    ]

    # --- DIAGNÓSTICO ---
    po_total = scalar(cur, "SELECT SUM(monto_total) FROM v_ordenes_compra") or 0.0
    diagnostics = {
        "db_path": db_path,
        "has_sales_invoices": bool(scalar(cur, "SELECT COUNT(*) FROM v_facturas_venta")),
        "has_budgets": bool(scalar(cur, "SELECT COUNT(*) FROM v_presupuesto_totales")),
        "po_total": po_total
    }

    return {
        "generated_at": datetime.datetime.utcnow().isoformat()+"Z",
        "cash": cash,
        "revenue": revenue,
        "margin": {"month_pct": None, "plan_pct": None, "delta_pp": None, "top_projects": []},
        "working_cap": {"dso": None, "dpo": None, "dio": None, "ccc": None,
                         "ar": {"d1_30":0, "d31_60":0, "d60_plus":0},
                         "ap": {"d7":0, "d14":0, "d30":0}},
        "backlog": {"total": None, "cobertura_meses": None, "pipeline_weighted": None, "pipeline_vs_goal_pct": None},
        "projects": projects,
        "risk": risk,
        "alerts": alerts,
        "actions": actions,
        "diagnostics": diagnostics
    }

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='data/chipax_data.db')
    ap.add_argument('--out', default='data/ceo_overview.json')
    a = ap.parse_args()
    data = build_payload(a.db)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Wrote {a.out}")
```

---

## 3) Endpoint API — `/api/ceo/overview`
```python
# backend/api_ceo_overview.py
from flask import Blueprint, jsonify
import sqlite3, json, datetime

bp = Blueprint('ceo', __name__)
DB = 'data/chipax_data.db'

def db():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; return con

@bp.get('/api/ceo/overview')
def ceo_overview():
    con = db(); cur = con.cursor()
    # Reutiliza las mismas consultas del script; aquí abreviado por espacio
    def scalar(sql, params=()):
        cur.execute(sql, params); r=cur.fetchone(); return (list(r)[0] if r else None)
    def q(sql, params=()):
        cur.execute(sql, params); return [dict(x) for x in cur.fetchall()]

    # Cash hoy (saldo por cuenta, si existe)
    cash_today = 0.0
    for r in q("SELECT bank_name, account_number, MAX(date(fecha)) AS last_date FROM bank_movements GROUP BY bank_name, account_number"):
        if r['last_date'] is None: continue
        cur.execute("""
          SELECT saldo FROM bank_movements
          WHERE bank_name IS ? AND account_number IS ? AND date(fecha)=?
          ORDER BY datetime(fecha) DESC, id DESC LIMIT 1
        """, (r['bank_name'], r['account_number'], r['last_date']))
        row = cur.fetchone(); cash_today += float(row['saldo'] or 0) if row else 0

    month = scalar("SELECT SUM(monto_total) FROM v_facturas_venta WHERE strftime('%Y-%m', fecha)=strftime('%Y-%m','now')") or 0.0
    ytd   = scalar("SELECT SUM(monto_total) FROM v_facturas_venta WHERE date(fecha)>=date(strftime('%Y-01-01','now'))") or 0.0

    proj_total = scalar("SELECT COUNT(DISTINCT project_id) FROM v_ordenes_compra WHERE project_id IS NOT NULL") or 0
    with_pc    = scalar("SELECT COUNT(DISTINCT project_id) FROM v_presupuesto_totales") or 0

    without_pc = max(0, proj_total - with_pc)

    payload = {
      "generated_at": datetime.datetime.utcnow().isoformat()+"Z",
      "cash": {"today": cash_today, "d7": None, "d30": None, "d60": None, "d90": None, "shortfall_7": None, "shortfall_30": None},
      "revenue": {"month": {"real": month, "plan": None, "delta_pct": None}, "ytd": {"real": ytd, "plan": None, "delta_pct": None}, "spark": []},
      "margin": {"month_pct": None, "plan_pct": None, "delta_pp": None, "top_projects": []},
      "working_cap": {"dso": None, "dpo": None, "dio": None, "ccc": None, "ar": {"d1_30":0, "d31_60":0, "d60_plus":0}, "ap": {"d7":0, "d14":0, "d30":0}},
      "backlog": {"total": None, "cobertura_meses": None, "pipeline_weighted": None, "pipeline_vs_goal_pct": None},
      "projects": {"total": int(proj_total), "on_budget": None, "over_budget": None, "without_pc": int(without_pc), "three_way_violations": None, "wip_ep_to_invoice": None},
      "risk": {"score": 70 if without_pc>0 else 40, "reasons": (["Falta presupuesto en la mayoría de proyectos"] if without_pc>0 else [])},
      "alerts": ([{"kind":"data_quality","title":f"Falta presupuesto en {without_pc} proyectos","cta":"/presupuestos/importar"}] if without_pc>0 else []) + ([{"kind":"data_gap","title":"No hay facturas de venta cargadas (AR)","cta":"/ventas/importar"}] if ytd==0 else []),
      "actions": [{"title":"Importar presupuestos reales (XLSX)","cta":"/presupuestos/importar"}, {"title":"Importar facturas de venta desde Chipax/SII","cta":"/ventas/importar"}],
      "diagnostics": {"has_sales_invoices": bool(scalar("SELECT COUNT(*) FROM v_facturas_venta")), "has_budgets": bool(scalar("SELECT COUNT(*) FROM v_presupuesto_totales"))}
    }
    return jsonify(payload)
```
> Registrar en `backend/server.py`:
```python
from api_ceo_overview import bp as ceo_bp
app.register_blueprint(ceo_bp)
```

---

## 4) Cómo evoluciona a la versión “full”
Cuando cargues **Ventas (AR)**, **Presupuestos (PC)** y conciliaciones, el mismo endpoint puede ampliar:
- `cash.d7/d30/d60/d90` desde `recon_links` + obligaciones (nómina, impuestos, AP programados).
- `margin.*` con AP facturado real (no OC).
- `projects.on_budget/over_budget` usando `v_project_financial_kpis`.
- `risk` combinando 3‑way (si crea `v_3way_status_po_line_ext`).

---

## 5) QA útil
```sql
SELECT COUNT(*) FROM v_facturas_venta;         -- ¿Hay ventas?
SELECT COUNT(*) FROM v_presupuesto_totales;     -- ¿Hay presupuestos?
SELECT COUNT(DISTINCT project_id) FROM v_ordenes_compra; -- ¿Cuántos proyectos con PO?
SELECT SUM(monto_total) FROM v_ordenes_compra;  -- Total comprometido OC
```

---

### Cierre
Este builder produce hoy un **payload real** con lo que hay en tu DB y deja listo el endpoint. A medida que importes AR/PC/conciliaciones, el mismo contrato de datos se enriquece sin romper el frontend del **CEO Dashboard**.

