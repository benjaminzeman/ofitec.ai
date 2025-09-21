# OFITEC — **Control Financiero 360** (Especificación + Implementación)
> Tablero “estado del arte” para controlar la salud financiera de cada proyecto en **una sola vista**, con acciones inmediatas y cerebro asistente. Cumple **docs_oficiales**: *Ley de Puertos* (UI 3001, API 5555), *DB Canónica* (consultar por vistas), y coherencia con módulos **PO/GRN/Facturas/Conciliación/EP Subcontratos** ya definidos en Ofitec.

---

## 1) Objetivo y principios
- **Panorama → Diagnóstico → Acción** en 10s: ver PC, PO/GRN/AP, Ventas/EP/AR, Riesgo y qué hacer ahora.
- **3‑way real** en costos (OC↔GRN↔Factura) y circuito AR (EP↔Factura Venta↔Cobro).
- **Explicabilidad**: cada KPI tiene breakdown “¿Por qué?” y log de fuentes.
- **Asistente**: sugerencias contextuales (importar presupuesto, asociar OC↔Factura, crear GRN, generar EP, conciliar cobros/pagos).
- **Compatibilidad**: sólo lee de **vistas canónicas**; escribe mediante endpoints de acción ya definidos.

---

## 2) KPIs canónicos por proyecto
> Todas las métricas salen de vistas/tablas canónicas ya presentes o agregadas en anexos previos.

**Costos**
- **PC (Presupuesto de Costos)**: `v_presupuesto_totales.total`.
- **PO Comprometido**: suma de `purchase_orders_unified.total_amount` (estados aprobados/abiertos).
- **GRN (Recepcionado)**: `SUM(qty_received_accum * unit_price)` por `v_po_line_received_accum` + `purchase_order_lines`.
- **Facturado AP (Gastado)**: `SUM(invoice_lines.qty * unit_price)`.
- **Pagado AP**: `SUM(v_ap_payments.amount)` (cartola conciliada).

**Ventas**
- **Contrato/Venta**: monto meta del proyecto (si existe) o acumulado de **EP aprobados** cliente.
- **EP cliente (Avance valorizado)**: suma período/acumulado.
- **Facturado Venta** y **Cobrado**: desde facturas de venta y conciliación AR.

**Derivadas**
- **Disponible** = `PC − PO`.
- **Desvío** (si no hay ventas) = `PC − Facturado AP`.
- **Margen** (si hay ventas) = `Ventas − Facturado AP`.
- **Avance físico %** = `EP_acumulado / Contrato`.
- **Riesgo (Score 0‑100)** = combinación ponderada de señales (ver §7).

---

## 3) Vista agregada por proyecto (SQLite + Postgres)
> Creamos **una** vista que entrega todo lo necesario para la tabla. Ajusta nombres si difieren.

### 3.1 SQLite
```sql
DROP VIEW IF EXISTS v_project_financial_kpis;
CREATE VIEW v_project_financial_kpis AS
WITH pc AS (
  SELECT project_id, SUM(total) AS pc
  FROM v_presupuesto_totales GROUP BY project_id
), po AS (
  SELECT o.zoho_project_name AS project_name, SUM(o.total_amount) AS po_total
  FROM purchase_orders_unified o
  GROUP BY o.zoho_project_name
), grn AS (
  SELECT pol.po_id, SUM(COALESCE(v.qty_received_accum,0) * pol.unit_price) AS grn_total
  FROM purchase_order_lines pol
  LEFT JOIN v_po_line_received_accum v ON v.po_line_id = pol.po_line_id
  GROUP BY pol.po_id
), grn_by_project AS (
  SELECT o.zoho_project_name AS project_name, SUM(g.grn_total) AS grn_total
  FROM grn g JOIN purchase_orders_unified o ON o.po_id = g.po_id
  GROUP BY o.zoho_project_name
), ap AS (
  SELECT o.zoho_project_name AS project_name, SUM(il.qty * il.unit_price) AS ap_facturado
  FROM invoice_lines il
  JOIN purchase_order_lines pol ON pol.po_line_id = il.po_line_id
  JOIN purchase_orders_unified o ON o.po_id = pol.po_id
  GROUP BY o.zoho_project_name
), ap_pay AS (
  SELECT i.project_name, SUM(p.amount) AS ap_pagado
  FROM v_ap_payments p
  JOIN v_ap_invoices_with_project i ON i.invoice_id = p.invoice_id
  GROUP BY i.project_name
), ventas AS (
  SELECT project_id, SUM(total_contrato) AS contrato, SUM(ep_acumulado) AS ep_acum,
         SUM(fact_venta) AS fact_venta, SUM(cobrado) AS cobrado
  FROM v_projects_sales_rollup GROUP BY project_id
)
SELECT
  pr.id AS project_id,
  pr.name AS project_name,
  COALESCE(pc.pc,0) AS pc,
  COALESCE(po.po_total,0) AS po_total,
  COALESCE(grn_by_project.grn_total,0) AS grn_total,
  COALESCE(ap.ap_facturado,0) AS ap_facturado,
  COALESCE(ap_pay.ap_pagado,0) AS ap_pagado,
  COALESCE(v.contrato,0) AS contrato,
  COALESCE(v.ep_acum,0) AS ep_acum,
  COALESCE(v.fact_venta,0) AS fact_venta,
  COALESCE(v.cobrado,0) AS cobrado
FROM projects pr
LEFT JOIN pc ON pc.project_id = pr.id
LEFT JOIN po ON po.project_name = pr.name
LEFT JOIN grn_by_project ON grn_by_project.project_name = pr.name
LEFT JOIN ap ON ap.project_name = pr.name
LEFT JOIN ap_pay ON ap_pay.project_name = pr.name
LEFT JOIN ventas v ON v.project_id = pr.id;
```

### 3.2 Postgres (idéntica lógica; `numeric` y `JOIN` igual)
> Si tu catálogo de proyectos usa `proyectos` en vez de `projects`, cambia en `FROM/JOIN`.

---

## 4) Endpoint 5555 (API) — `/api/projects/finance`
Entrega KPIs, explicaciones y contadores de riesgo/violaciones.

```py
# backend/api_projects_finance.py
from flask import Blueprint, request, jsonify
import sqlite3

bp = Blueprint('proj_fin', __name__)
DB = 'data/chipax_data.db'

def db():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; return con

@bp.get('/api/projects/finance')
def projects_finance():
    page = int(request.args.get('page',1)); per = int(request.args.get('per_page',50))
    con = db(); cur = con.cursor()
    cur.execute('SELECT COUNT(1) AS n FROM v_project_financial_kpis'); total = cur.fetchone()['n']
    cur.execute('SELECT * FROM v_project_financial_kpis LIMIT ? OFFSET ?', (per, (page-1)*per))
    rows = [dict(r) for r in cur.fetchall()]
    # derivadas rápidas + placeholders de riesgo/violaciones
    for r in rows:
        r['disponible'] = max(0.0, (r['pc'] or 0) - (r['po_total'] or 0))
        r['desvio'] = (r['pc'] or 0) - (r['ap_facturado'] or 0)
        r['margen'] = (r['contrato'] or 0) - (r['ap_facturado'] or 0)
        r['avance_pct'] = 0.0 if not r['contrato'] else round((r['ep_acum'] or 0) / r['contrato'] * 100, 2)
        r['viol_3way'] = 0  # poblar desde v_ap_reconciliation_flags_pg agregada por proyecto
        r['aging_ap30'] = 0 # poblar desde vista aging
        r['risk_score'] = compute_risk(r)
        r['why'] = build_why(r)
    return jsonify({
      'items': rows,
      'page_context': {'page':page,'per_page':per,'total':total,'has_more_page': page*per < total}
    })

# Ejemplo simple; reemplazar por función con pesos configurables
def compute_risk(r):
    pc = r.get('pc') or 0; po = r.get('po_total') or 0
    comprometido_ratio = min(1.5, po/pc) if pc>0 else 1.0
    gasto_vs_avance = 0.0
    if r.get('contrato') and r['contrato']>0:
        gasto_vs_avance = max(0.0, ((r.get('ap_facturado') or 0)/(r['contrato'])) - (r.get('avance_pct') or 0)/100)
    base = 40*comprometido_ratio + 30*gasto_vs_avance + 20*(r.get('viol_3way') or 0)/10 + 10*(r.get('aging_ap30') or 0)/10
    return int(max(0, min(100, round(base))))

def build_why(r):
    w=[];
    if (r.get('pc') or 0)==0: w.append('Falta presupuesto')
    if (r.get('po_total') or 0)>(r.get('pc') or 0)>0: w.append('PO supera presupuesto')
    if (r.get('contrato') or 0)>0 and (r.get('ap_facturado') or 0)>(r.get('contrato') or 1)* (r.get('avance_pct') or 0)/100: w.append('Gasto por sobre avance')
    return w
```
> Registrar en `backend/server.py`: `from api_projects_finance import bp as proj_fin_bp; app.register_blueprint(proj_fin_bp)`.

---

## 5) UI (Next.js/Tailwind) — Tabla con mini-barras, chips y acciones

### 5.1 Componentes base
```tsx
// components/MiniBar.tsx
'use client';
export default function MiniBar({ parts }:{ parts:{label:string; value:number}[] }){
  const total = parts.reduce((a,b)=>a+b.value,0) || 1;
  return (
    <div className="w-full h-2 rounded bg-neutral-100 overflow-hidden">
      <div className="flex h-full">
        {parts.map((p,i)=> (
          <div key={i} style={{width:`${(p.value/total)*100}%`}} className="h-full border-r last:border-r-0" title={`${p.label}: ${p.value.toLocaleString()}`} />
        ))}
      </div>
    </div>
  );
}
```

```tsx
// components/RiskChip.tsx
'use client';
export default function RiskChip({ score }:{ score:number }){
  const tone = score>=70?'border-rose-600':score>=40?'border-amber-500':'border-emerald-500';
  return <span className={`px-2 py-0.5 text-xs rounded-full border ${tone}`}>Riesgo {score}</span>;
}
```

```tsx
// components/WhyPopover.tsx
'use client';
import { useState } from 'react';
export default function WhyPopover({ items }:{ items:string[] }){
  const [open,setOpen]=useState(false);
  return (
    <span className="text-xs">
      <button className="underline" onClick={()=>setOpen(!open)}>¿Por qué?</button>
      {open && (
        <div className="absolute z-50 mt-1 p-2 bg-white border rounded shadow text-xs space-y-1">
          {items?.length? items.map((x,i)=>(<div key={i}>• {x}</div>)) : <div>Sin observaciones</div>}
        </div>
      )}
    </span>
  );
}
```

```tsx
// pages/proyectos/financiero/page.tsx
'use client';
import { useEffect, useState } from 'react';
import MiniBar from '@/components/MiniBar';
import RiskChip from '@/components/RiskChip';
import WhyPopover from '@/components/WhyPopover';

export default function Financiero(){
  const [rows,setRows]=useState<any[]>([]);
  useEffect(()=>{(async()=>{
    const r = await fetch('http://localhost:5555/api/projects/finance');
    const j = await r.json(); setRows(j.items||[]);
  })();},[]);

  return (
    <div className="p-4">
      <h1 className="text-xl font-semibold mb-3">Proyectos — Vista Financiera</h1>
      <div className="rounded-2xl border overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-neutral-500">
              <th className="p-2">Proyecto</th>
              <th className="p-2">PC vs PO</th>
              <th className="p-2">PO/GRN/AP/Pagado</th>
              <th className="p-2">Contrato/EP/Fact/Cobrado</th>
              <th className="p-2">Avance</th>
              <th className="p-2">Riesgo</th>
              <th className="p-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r=> (
              <tr key={r.project_id} className="border-t">
                <td className="p-2">{r.project_name}</td>
                <td className="p-2">
                  <div className="text-xs mb-1">PC {Math.round(r.pc).toLocaleString()} — PO {Math.round(r.po_total).toLocaleString()}</div>
                  <MiniBar parts={[{label:'PC',value:r.pc||1},{label:'PO',value:r.po_total||0}]} />
                  <div className="mt-1"><WhyPopover items={r.why} /></div>
                </td>
                <td className="p-2">
                  <MiniBar parts={[
                    {label:'PO',value:r.po_total||0},
                    {label:'GRN',value:r.grn_total||0},
                    {label:'AP',value:r.ap_facturado||0},
                    {label:'Pagado',value:r.ap_pagado||0},
                  ]} />
                </td>
                <td className="p-2">
                  <MiniBar parts={[
                    {label:'Contrato',value:r.contrato||0},
                    {label:'EP',value:r.ep_acum||0},
                    {label:'Fact',value:r.fact_venta||0},
                    {label:'Cobrado',value:r.cobrado||0},
                  ]} />
                </td>
                <td className="p-2">{r.avance_pct?.toFixed(1)}%</td>
                <td className="p-2"><RiskChip score={r.risk_score||0} /></td>
                <td className="p-2 flex gap-2">
                  <a className="border px-2 py-1 rounded" href={`/proyectos/${r.project_id}`}>Abrir</a>
                  <a className="border px-2 py-1 rounded" href={`/acciones?proyecto=${r.project_id}`}>Sugerencias</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

**Interacciones sugeridas (CTAs en modal “Sugerencias”)**
- **Falta Presupuesto** → abre **importador** con mapeo difuso.
- **PO > PC** → lista OCs que superan; opción de **revisar/cerrar**.
- **Factura > Recepción/OC** → abre **panel 3‑way**.
- **EP sin facturar** → botón **Generar factura de venta**.
- **Facturas vencidas** → abre **Portal Proveedor/Cliente** o conciliación.

---

## 6) Riesgo (Score) — fórmula y pesos
> Personalizable por empresa. Valores iniciales recomendados:

```
score = clamp(0..100,
  40 * min(1.5, PO/PC)                                # presión sobre presupuesto
+ 30 * max(0, (Gastado/Ventas) - AvanceFisico)        # gasto por sobre avance
+ 20 * (violaciones_3way_normalizadas)               # calidad de control
+ 10 * (aging_AP_30_normalizado)                     # presión de caja
)
```
- Mostrar **razones top‑3** debajo del chip (viene en `why`).

---

## 7) Accesibilidad, performance y gobernanza
- **Accesible** (teclado, contraste, tooltips textuales).
- **Rápida**: la API agrega todo en **una consulta** a la vista; incluir **paginación** y `?project_like=`.
- **Auditable**: cada KPI muestra fuente (vista y fecha); logs en servidor.

---

## 8) Quickstart (local)
1) Crear vista: ejecutar SQL de §3 en tu DB.
2) Registrar endpoint de §4 en `server.py`.
3) Añadir página React de §5.
4) Abrir `http://localhost:3001/proyectos/financiero`.

---

## 9) Roadmap corto
- Enriquecer `risk_score` con **violaciones 3‑way** reales por proyecto y **aging** desde vistas.
- Añadir **drawer de Sugerencias** con acciones directas (usar drawers ya creados: **ReconcileDrawer**, **APMatchDrawer**, **GRNReceiveForm**, **CertificateWizard**).
- Exportar **PDF**/XLSX del tablero.

---

## 10) Notas para Copilot
- Mantener **Ley de Puertos** (UI 3001, API 5555) y **DB Canónica** (consultar vistas).
- No romper contratos existentes; si falta alguna vista auxiliar, crearla con nombre `v_*` y documentarla.
- Asegurar **422** y mensajes claros en acciones que salgan del tablero (3‑way, EP, conciliación).
- Tests E2E:
  - proyecto con **PC=0** (debe mostrar chip “Falta Presupuesto”),
  - proyecto **PO>PC** (riesgo alto y CTA),
  - proyecto con **viol_3way>0**,
  - proyecto con **ventas** (mostrar *Margen* correcto) vs sin ventas (mostrar *Desvío*).

