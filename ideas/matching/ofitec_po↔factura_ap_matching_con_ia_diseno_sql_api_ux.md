# OFITEC — **Asociación Orden de Compra (OC) ↔ Factura de Compra (AP)** con IA
> Objetivo: que Ofitec **sugiera automáticamente** la(s) OC correcta(s) para cada factura de compra y el usuario sólo **acepte** o ajuste (split/merge) con 1–2 clics. Compatible con **entregas parciales** (una OC → varias facturas) y **facturas consolidadas** (varias OC → una factura), respetando **3‑way match** (OC ↔ Recepción ↔ Factura), *Ley de Puertos* (3001/5555), *DB Canónica* y vistas ya definidas.

---

## 0) Principios
- **Auto‑matching por defecto**: el sistema propone; el humano confirma. Si `confidence ≥ 0.92`, botón **Aceptar #1** (Enter). Si `≥ 0.97`, **auto‑asociación segura** (opcional, con log y deshacer).
- **3‑way real**: *Factura ≤ Recepción acumulada* **y** *Factura ≤ OC* (por línea y total). Si no hay Recepción, sugerir **crear GRN** (cuando aplique materiales) o justificar *servicio sin recepción*.
- **Tolerancias** configurables (cantidad/importe/fecha) por **proveedor**, **familia** o **proyecto**.
- **Explicabilidad**: toda sugerencia muestra **razones** (monto, fecha, RUT/alias, folio, descripción). Nada de caja negra.
- **Auditoría**: `ap_match_events` (quién, qué, cuándo, por qué), y `ap_po_links` (N↔M con asignación por línea o monto).

---

## 1) Modelo de Datos (mínimo)
> Extiende lo existente (`purchase_orders_unified`, `purchase_order_lines`, `ap_invoices`, `invoice_lines`, `goods_receipt_lines`).

```sql
-- Enlace N↔M entre Facturas AP y OC (a nivel línea o monto)
CREATE TABLE IF NOT EXISTS ap_po_links (
  id INTEGER PRIMARY KEY,
  invoice_id INTEGER NOT NULL,           -- ap_invoices.id
  invoice_line_id INTEGER,               -- opcional, si la factura tiene detalle
  po_id TEXT,                            -- OC (header)
  po_line_id TEXT,                       -- línea OC (si aplica)
  amount REAL NOT NULL,                  -- monto asignado
  qty REAL,                              -- opcional: cantidad asignada
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  created_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_ap_po_links_inv ON ap_po_links(invoice_id);
CREATE INDEX IF NOT EXISTS idx_ap_po_links_poline ON ap_po_links(po_line_id);

-- Bitácora de sugerencias/decisiones (para aprendizaje)
CREATE TABLE IF NOT EXISTS ap_match_events (
  id INTEGER PRIMARY KEY,
  invoice_id INTEGER NOT NULL,
  source_json TEXT NOT NULL,     -- snapshot de factura
  candidates_json TEXT NOT NULL, -- top-N sugeridos
  chosen_json TEXT,              -- ganador/es
  confidence REAL,
  reasons TEXT,
  accepted INTEGER,              -- 1 sí, 0 no
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  user_id TEXT
);
```

**Vistas de apoyo**
```sql
-- Estado de facturación por línea de OC (lo que ya está facturado)
DROP VIEW IF EXISTS v_po_line_billed_accum;
CREATE VIEW v_po_line_billed_accum AS
SELECT il.po_line_id,
       SUM(il.qty) AS qty_invoiced,
       SUM(il.qty * il.unit_price) AS amt_invoiced
FROM invoice_lines il
GROUP BY il.po_line_id;

-- Tablero 3‑way (OC vs Recepción vs Factura) por línea
DROP VIEW IF EXISTS v_3way_status_po_line_ext;
CREATE VIEW v_3way_status_po_line_ext AS
SELECT
  pol.po_line_id,
  pol.po_id,
  pol.qty AS po_qty,
  pol.unit_price AS po_unit_price,
  COALESCE(rec.qty_received_accum,0) AS recv_qty,
  COALESCE(bill.qty_invoiced,0)      AS inv_qty,
  CASE
    WHEN COALESCE(bill.qty_invoiced,0) <= COALESCE(rec.qty_received_accum,0)
     AND COALESCE(rec.qty_received_accum,0) <= pol.qty THEN 'matching'
    WHEN COALESCE(bill.qty_invoiced,0) > COALESCE(rec.qty_received_accum,0) THEN 'invoice_over_receipt'
    WHEN COALESCE(rec.qty_received_accum,0) > pol.qty THEN 'over_received'
    ELSE 'under_received'
  END AS match_status
FROM purchase_order_lines pol
LEFT JOIN v_po_line_received_accum rec ON rec.po_line_id = pol.po_line_id
LEFT JOIN v_po_line_billed_accum bill  ON bill.po_line_id = pol.po_line_id;
```

---

## 2) Motor de Sugerencias (algoritmo)
### 2.1 Generación de candidatos
1) **Filtrado fuerte**:
   - Por **proveedor** (RUT/ID exacto o alias) y **proyecto** (si factura trae proyecto).  
   - PO **abiertas** o **parcialmente facturadas** en ventana de **fecha** (p.ej., −30 a +15 días vs. fecha factura).  
2) **Candidatos por monto**: buscar líneas de OC cuya suma (una o varias) ≈ **monto factura** dentro de `amount_tol` (p.ej., 1–2%).  
3) **Contenido/folio**: regex de **nº OC**/referencias en el PDF/OCR/csv; similitud de **descripción** y **UOM** (normalizadas).  
4) **Recepciones**: priorizar líneas con **recepción** suficiente (GRN) cuando aplique materiales.

### 2.2 Puntaje (ranking)
- **Monto** (50%): exacto = 1.0; delta% → `exp(-k·|Δ%|)`.  
- **Fecha** (20%): distancia en días, penalizando hacia atrás/adelante según política.  
- **Identidad** (20%): proveedor exacto, RUT, cuenta/alias, *nº OC en factura*.  
- **Contenido** (10%): `cosine` de tokens de descripción, match de UOM y PU.  
- **Bonos**: si *Recepción ≥ Facturado* por línea, +0.05.

### 2.3 Split/Merge inteligente
- **Una factura → varias OC**: *subset‑sum* greedy sobre candidatos del mismo proveedor y proyecto.  
- **Una OC → varias facturas**: respetar *saldo facturable* por línea (`po_qty - inv_qty`) y por monto.

### 2.4 Learning (simple sin MLOps)
- Guardar **positivos/negativos** en `ap_match_events`.  
- Actualizar **alias** de proveedor y patrones de referencia (nº OC, prefijos) por proveedor.  
- Recalibrar pesos si el usuario cambia seguido la 1ª sugerencia.

---

## 3) Endpoint API (5555)
```yaml
POST /api/ap-match/suggestions
  body: { invoice_id?:number, vendor_id?:number, project_id?:number, amount:number, date:'YYYY-MM-DD', currency:'CLP'|'USD', amount_tol?:0.02, days?:30 }
  200: { items: [ { candidate: { po_id, lines:[{po_line_id, qty_avail, unit_price}], coverage:{amount, pct}, confidence:0..1, reasons:[...] } ] }

POST /api/ap-match/preview
  body: { invoice_id, links:[{po_id, po_line_id?, amount, qty?}] }
  200: { ok:true, deltas: { by_po:{...}, by_line:{...}, three_way_summary:{ violations:[], warnings:[] } } }

POST /api/ap-match/confirm
  body: { invoice_id, links:[...], metadata:{ user_id, notes }, confidence, reasons }
  200: { ok:true, ap_po_links_created:n, three_way:{ status:'ok'|'violations', details:[...] } }
```

---

## 4) UX — Flujos
### 4.1 Desde **Factura de Compra**
- Botón **“Asociar OC”** → *drawer* con **Top‑5** sugerencias (chips de razones: monto, fecha, nº OC, GRN, descripción).  
- Acción **Aceptar #1** (Enter) o **Dividir** (selecciona 2–3 OCs para cubrir monto).  
- Semáforo **3‑way**: verde (ok), ámbar (sin GRN suficiente), rojo (Factura>OC o >Recepción).  
- Si rojo: botón **“Crear Recepción”** (si material) o **“Justificar servicio”**.

### 4.2 Desde **Orden de Compra**
- Botón **“Agregar factura”** → sugiere facturas del mismo proveedor dentro de rango de fecha/monto.  
- Mostrar **% facturado** por línea y **saldo** (cantidad y monto).  
- Acción rápida: **Asignar** factura completa a líneas pendientes (auto‑prorrateo por saldo).

### 4.3 Desde **Recepciones (GRN)**
- Botón **“Facturar recepciones”** → sugiere facturas que cubren esas recepciones (clásico *receipts to invoice*).

---

## 5) Reglas/Tolerancias (config)
- **Cantidad**: ±X unidades o ±Y%.  
- **Importe**: ±Z% por línea/cabecera; tolerancia distinta para **flete/seguros**.  
- **Fecha**: ventana −N / +M días; especial para **servicios**.  
- **UOM**: tabla de **equivalencias** (kg ↔ t; caja ↔ und×n).  
- **Moneda**: convertir por tipo de cambio del día; tolerancia adicional por redondeo.

---

## 6) Validaciones duras (422)
- `invoice_over_po`: factura excede el **total OC** (línea o cabecera).  
- `invoice_over_receipt`: factura excede **recepción acumulada**.  
- `vendor_mismatch`: proveedor de factura ≠ proveedor de OC.  
- `uom_mismatch`: unidades incompatibles sin equivalencia.  
- `over_allocation`: suma de `ap_po_links` para la línea excede su saldo.

---

## 7) Performance/Índices
- Índices compuestos: `purchase_order_lines(po_id, po_line_id)`, `invoice_lines(invoice_id, po_line_id)`.  
- Materializar **saldos**: vista materializada `v_po_line_balances` con `qty_remaining` y `amt_remaining`.

---

## 8) Casos de borde
- **Facturas con flete/impuestos** fuera de OC → sugerir **línea de ajuste** (cuenta contable configurada).  
- **Notas de crédito** → enlazar con `ap_po_links` negativos y descontar de saldos.  
- **Contratos (servicios)** → permitir sin GRN, pero exigir **certificado**/EP o *service receipt*.

---

## 9) Ejemplos de payloads
```json
// Sugerencias para factura 7711
{"vendor_id": 17, "invoice_id": 7711, "project_id": 42, "amount": 25369786, "date": "2025-09-10", "currency": "CLP"}

// Confirmar split en 2 OCs
{"invoice_id":7711, "links":[
  {"po_id":"PO-2025-00123","po_line_id":"POL-3","amount":18000000},
  {"po_id":"PO-2025-00007","po_line_id":"POL-1","amount":7369786}
], "confidence":0.93, "reasons":["monto=split","fecha=+2d","alias proveedor"]}
```

---

## 10) Notas para Copilot
- Reutilizar `v_po_line_received_accum` y `v_3way_status_po_line` ya creadas; añadir `v_po_line_billed_accum` y `v_3way_status_po_line_ext` (arriba).  
- Implementar `/api/ap-match/*` en **5555**; garantizar **422** en reglas duras.  
- UI: *drawer* reutilizable (mismo patrón del **ReconcileDrawer**); chips con razones; atajo Enter.  
- Persistir decisiones en `ap_match_events` y enlaces en `ap_po_links`; recalcular saldos y actualizar semáforos 3‑way.  
- Tests:
  - 1 OC → 2 facturas (parciales),
  - 2 OCs → 1 factura (consolidada),
  - servicio sin GRN,
  - moneda distinta,
  - tolerancias límite.


---

## Addenda — Postgres + Endpoints 5555 + Drawer React “Asociar OC”
> Extiende el diseño para **OC↔Factura (AP) Matching con IA** con SQL **Postgres**, endpoints listos y un **drawer** reutilizable en la UI.

### A) SQL — Postgres (vistas y saldos)
```sql
-- 1) Facturado acumulado por línea de OC
DROP VIEW IF EXISTS v_po_line_billed_accum_pg;
CREATE VIEW v_po_line_billed_accum_pg AS
SELECT il.po_line_id,
       SUM(il.qty)                        AS qty_invoiced,
       SUM((il.qty * il.unit_price))::numeric(18,2) AS amt_invoiced
FROM invoice_lines il
GROUP BY il.po_line_id;

-- 2) 3‑way por línea (con recepciones y facturación)
DROP VIEW IF EXISTS v_3way_status_po_line_ext_pg;
CREATE VIEW v_3way_status_po_line_ext_pg AS
SELECT
  pol.po_line_id,
  pol.po_id,
  pol.qty                                AS po_qty,
  pol.unit_price                         AS po_unit_price,
  COALESCE(rec.qty_received_accum,0)     AS recv_qty,
  COALESCE(bill.qty_invoiced,0)          AS inv_qty,
  CASE
    WHEN COALESCE(bill.qty_invoiced,0) <= COALESCE(rec.qty_received_accum,0)
     AND COALESCE(rec.qty_received_accum,0) <= pol.qty THEN 'matching'
    WHEN COALESCE(bill.qty_invoiced,0) >  COALESCE(rec.qty_received_accum,0) THEN 'invoice_over_receipt'
    WHEN COALESCE(rec.qty_received_accum,0) >  pol.qty THEN 'over_received'
    ELSE 'under_received'
  END AS match_status
FROM purchase_order_lines pol
LEFT JOIN v_po_line_received_accum   rec  ON rec.po_line_id  = pol.po_line_id
LEFT JOIN v_po_line_billed_accum_pg  bill ON bill.po_line_id = pol.po_line_id;

-- 3) Saldos por línea de OC (qty/monto restantes)
DROP VIEW IF EXISTS v_po_line_balances_pg;
CREATE VIEW v_po_line_balances_pg AS
WITH billed AS (
  SELECT il.po_line_id,
         SUM(il.qty) AS qty_invoiced,
         SUM(il.qty * il.unit_price)::numeric(18,2) AS amt_invoiced
  FROM invoice_lines il
  GROUP BY il.po_line_id
), recv AS (
  SELECT r.po_line_id,
         SUM(r.qty_received_accum) AS qty_received
  FROM v_po_line_received_accum r
  GROUP BY r.po_line_id
)
SELECT pol.po_line_id,
       pol.po_id,
       pol.qty                                        AS po_qty,
       COALESCE(recv.qty_received,0)                  AS qty_received,
       COALESCE(billed.qty_invoiced,0)                AS qty_invoiced,
       (pol.qty - COALESCE(billed.qty_invoiced,0))    AS qty_remaining,
       (pol.qty * pol.unit_price)::numeric(18,2)      AS amt_po,
       COALESCE(billed.amt_invoiced,0)                AS amt_invoiced,
       ((pol.qty * pol.unit_price) - COALESCE(billed.amt_invoiced,0))::numeric(18,2) AS amt_remaining
FROM purchase_order_lines pol
LEFT JOIN billed ON billed.po_line_id = pol.po_line_id
LEFT JOIN recv   ON recv.po_line_id   = pol.po_line_id;
```

---

### B) Endpoints 5555 — `/api/ap-match/*` (Flask)
```py
# backend/ap_match_api.py
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import sqlite3

bp = Blueprint('apmatch', __name__)
DB = 'data/chipax_data.db'  # ajustar segun env

class Unprocessable(ValueError):
    def __init__(self, error, detail=None, **extra):
        self.payload = {'error': error, 'detail': detail}; self.payload.update(extra)

@bp.errorhandler(Unprocessable)
def _u(e): return jsonify(e.payload), 422

def db():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; return con

@bp.post('/api/ap-match/suggestions')
def suggestions():
    b = request.get_json(force=True)
    vendor_id = b.get('vendor_id'); amount = float(b.get('amount', 0)); days = int(b.get('days',30)); tol = float(b.get('amount_tol',0.02))
    date = b.get('date')
    if not vendor_id or not amount or not date:
        raise Unprocessable('invalid_payload','vendor_id, amount y date son requeridos')
    con = db(); cur = con.cursor()
    # 1) Candidatos por proveedor, ventana de tiempo y saldo > 0
    cur.execute('''
      SELECT bal.po_id, bal.po_line_id, bal.qty_remaining, bal.amt_remaining, pol.unit_price, u.vendor_id
      FROM v_po_line_balances_pg bal
      JOIN purchase_order_lines pol ON pol.po_line_id = bal.po_line_id
      JOIN purchase_orders_unified u ON u.po_id = bal.po_id
      WHERE u.vendor_id = ? AND bal.amt_remaining > 0
    ''',(vendor_id,))
    rows = cur.fetchall()
    # 2) Greedy subset por monto (simple)
    cand = []
    target_min, target_max = amount*(1-tol), amount*(1+tol)
    rows_sorted = sorted(rows, key=lambda r: r['amt_remaining'], reverse=True)
    acc = 0.0; pick=[]
    for r in rows_sorted:
        if acc + r['amt_remaining'] <= target_max:
            pick.append(dict(r)); acc += r['amt_remaining']
        if acc >= target_min: break
    if pick:
        cand.append({
          'candidate': {
            'po_id': list({x['po_id'] for x in pick}),
            'lines': [{'po_line_id':x['po_line_id'],'qty_avail':x['qty_remaining'],'unit_price':x['unit_price']} for x in pick],
            'coverage': {'amount': acc, 'pct': round(acc/amount,4)}
          },
          'confidence': min(0.99, 0.7 + min(0.3, abs(acc-amount)/max(amount,1e-6))),
          'reasons': ['monto≈', f'saldo líneas={acc:.0f}']
        })
    return jsonify({'items': cand})

@bp.post('/api/ap-match/preview')
def preview():
    b = request.get_json(force=True)
    invoice_id = b.get('invoice_id'); links = b.get('links') or []
    if not invoice_id or not links: raise Unprocessable('invalid_payload','invoice_id y links requeridos')
    # Validaciones 3‑way (simplificadas)
    # TODO: chequear vendor match, UOM, y recepciones si aplica
    return jsonify({'ok': True, 'deltas': {'by_line': links}})

@bp.post('/api/ap-match/confirm')
def confirm():
    b = request.get_json(force=True)
    invoice_id = b.get('invoice_id'); links = b.get('links') or []
    if not invoice_id or not links: raise Unprocessable('invalid_payload','invoice_id y links requeridos')
    con = db(); cur = con.cursor()
    for l in links:
        cur.execute('''
          INSERT INTO ap_po_links(invoice_id, invoice_line_id, po_id, po_line_id, amount, qty, created_by)
          VALUES(?,?,?,?,?,?,?)
        ''',(invoice_id, l.get('invoice_line_id'), l.get('po_id'), l.get('po_line_id'), l.get('amount'), l.get('qty'), b.get('metadata',{}).get('user_id')))
    # log de evento
    cur.execute('''INSERT INTO ap_match_events(invoice_id, source_json, candidates_json, chosen_json, confidence, reasons, accepted, user_id)
                   VALUES(?,?,?,?,?,?,1,?)''',(
        invoice_id, b.get('source_json','{}'), b.get('candidates_json','[]'), b.get('chosen_json','[]'), b.get('confidence'), ','.join(b.get('reasons',[]) ), b.get('metadata',{}).get('user_id')
    ))
    con.commit()
    return jsonify({'ok': True, 'ap_po_links_created': len(links)})
```

> **Integración**: `from ap_match_api import bp as apmatch_bp` y `app.register_blueprint(apmatch_bp)` en `backend/server.py`.

---

### C) UI — Drawer “Asociar OC” (Next.js + Tailwind)
```tsx
'use client';
import React, { useEffect, useState } from 'react';

export default function APMatchDrawer({ invoice }:{ invoice:{id:number; vendor_id:number; amount:number; date:string} }){
  const [open,setOpen] = useState(true);
  const [items,setItems] = useState<any[]>([]);
  const [chosen,setChosen] = useState<any|null>(null);

  useEffect(()=>{(async()=>{
    const r = await fetch('/api/ap-match/suggestions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      vendor_id: invoice.vendor_id, amount: invoice.amount, date: invoice.date
    })});
    const j = await r.json(); setItems(j.items||[]);
  })();},[invoice.id]);

  async function confirm(){
    if(!chosen) return;
    const links = (chosen.candidate.lines||[]).map((l:any)=> ({ po_id: chosen.candidate.po_id[0], po_line_id: l.po_line_id, amount: Math.min(invoice.amount, l.qty_avail * l.unit_price) }))
    const r = await fetch('/api/ap-match/confirm',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      invoice_id: invoice.id, links, confidence: chosen.confidence, reasons: chosen.reasons, metadata:{user_id:'me'}
    })});
    const j = await r.json(); alert(`Asociadas ${j.ap_po_links_created} líneas`); setOpen(false);
  }

  if(!open) return null;
  return (
    <div className="fixed inset-y-0 right-0 w-[420px] bg-white border-l p-4 z-50 overflow-auto">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold">Asociar OC</h3>
        <button onClick={()=>setOpen(false)} className="text-sm">Cerrar</button>
      </div>
      <div className="space-y-2">
        {items.map((it:any,idx:number)=> (
          <div key={idx} className={`rounded-2xl border p-3 ${chosen===it?'ring-1':''}`}>
            <div className="flex items-center justify-between">
              <div className="text-sm">Candidato #{idx+1} • cobertura {Math.round((it.candidate.coverage?.pct||0)*100)}%</div>
              <div className="text-xs">conf {(it.confidence*100).toFixed(1)}%</div>
            </div>
            <div className="mt-1 text-xs text-neutral-500">{(it.reasons||[]).join(' • ')}</div>
            <div className="mt-2">
              <ul className="list-disc pl-4 text-sm">
                {(it.candidate.lines||[]).map((l:any)=> <li key={l.po_line_id}>{l.po_line_id} — saldo {l.qty_avail} × {l.unit_price}</li>)}
              </ul>
            </div>
            <div className="mt-2 flex gap-2">
              <button className="border px-2 py-1 rounded" onClick={()=>setChosen(it)}>Elegir</button>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <button className="border px-3 py-1 rounded" onClick={confirm} disabled={!chosen}>Confirmar</button>
      </div>
    </div>
  );
}
```

---

### D) QA y mejoras
- **Validaciones 3‑way** estrictas antes de `confirm`:
  - vendor de OC = vendor factura; suma `amount` por línea ≤ `amt_remaining`; si material, `qty ≤ recv_qty - inv_qty`.
- **Split/merge** UX: permitir seleccionar 2–3 candidatos y prorratear por saldo hasta cubrir monto.
- **Learning**: persistir `ap_match_events` con `accepted=1/0`; aumentar confianza a patrones de referencia del proveedor (nº OC en glosa, prefijos, alias).
- **Auto‑asociación segura** (opcional): si `confidence ≥ 0.97` y sin violaciones 3‑way → asociar y notificar.
```

