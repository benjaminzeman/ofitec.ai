# OFITEC — Entregables **Estados de Pago (Cliente)**
**Archivo vivo** con: SQL (SQLite + notas Postgres), API Flask (boilerplate listo para pegar) y Wizard React para importar EP desde Excel, con validaciones y vínculo a facturación AR y flujo de caja.

> Cumplir Ley de Puertos (3001/5555), DB Canónica (vistas/ids), Estrategia Visual. Responder errores críticos con **422** y payload explicativo.

---

## 1) SQL — Tablas y Vistas (SQLite flavor)
> Ajustar nombres si difieren. Fechas como `TEXT` (ISO yyyy-mm-dd). Para Postgres ver **1.4**.

### 1.1 Tablas base (contrato cliente + SOV)
```sql
CREATE TABLE IF NOT EXISTS client_contracts (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL,
  customer_id INTEGER NOT NULL,
  code TEXT,
  start_date TEXT, end_date TEXT,
  currency TEXT,
  payment_terms_days INTEGER DEFAULT 30,
  retention_pct REAL DEFAULT 0,
  status TEXT CHECK (status IN ('active','closed')) DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS client_sov_items (
  id INTEGER PRIMARY KEY,
  contract_id INTEGER NOT NULL,
  item_code TEXT,
  description TEXT,
  unit TEXT,
  qty REAL,
  unit_price REAL,
  line_total REAL,
  chapter TEXT,
  UNIQUE(contract_id, item_code)
);
CREATE INDEX IF NOT EXISTS idx_sov_contract ON client_sov_items(contract_id);
```

### 1.2 Estados de Pago (EP cliente)
```sql
CREATE TABLE IF NOT EXISTS ep_headers (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL,
  contract_id INTEGER,
  ep_number TEXT,
  period_start TEXT, period_end TEXT,
  submitted_at TEXT, approved_at TEXT,
  status TEXT CHECK (status IN ('draft','submitted','approved','rejected','invoiced','paid')) DEFAULT 'draft',
  retention_pct REAL,
  notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_ep_project ON ep_headers(project_id);
CREATE INDEX IF NOT EXISTS idx_ep_status ON ep_headers(status);

CREATE TABLE IF NOT EXISTS ep_lines (
  id INTEGER PRIMARY KEY,
  ep_id INTEGER NOT NULL,
  sov_item_id INTEGER,
  item_code TEXT,
  description TEXT,
  unit TEXT,
  qty_period REAL,
  unit_price REAL,
  amount_period REAL,
  qty_cum REAL,
  amount_cum REAL,
  chapter TEXT
);
CREATE INDEX IF NOT EXISTS idx_ep_lines_ep ON ep_lines(ep_id);

CREATE TABLE IF NOT EXISTS ep_deductions (
  id INTEGER PRIMARY KEY,
  ep_id INTEGER NOT NULL,
  type TEXT CHECK (type IN ('retention','advance_amortization','penalty','other')),
  description TEXT,
  amount REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ep_ded_ep ON ep_deductions(ep_id);

CREATE TABLE IF NOT EXISTS ep_files (
  id INTEGER PRIMARY KEY,
  ep_id INTEGER NOT NULL,
  drive_file_id TEXT, storage_url TEXT,
  kind TEXT CHECK (kind IN ('xlsx','pdf')),
  uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### 1.3 Facturación AR y cobranzas
```sql
CREATE TABLE IF NOT EXISTS ar_invoices (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL,
  customer_id INTEGER NOT NULL,
  ep_id INTEGER,
  invoice_number TEXT,
  invoice_date TEXT,
  due_date TEXT,
  amount_net REAL,
  tax_amount REAL,
  amount_total REAL,
  status TEXT CHECK (status IN ('draft','issued','paid','cancelled')) DEFAULT 'issued'
);
CREATE INDEX IF NOT EXISTS idx_ar_proj ON ar_invoices(project_id);
CREATE INDEX IF NOT EXISTS idx_ar_ep ON ar_invoices(ep_id);

CREATE TABLE IF NOT EXISTS ar_collections (
  id INTEGER PRIMARY KEY,
  invoice_id INTEGER NOT NULL,
  collected_date TEXT,
  amount REAL,
  method TEXT,
  bank_ref TEXT
);
CREATE INDEX IF NOT EXISTS idx_col_inv ON ar_collections(invoice_id);
```

### 1.4 Vistas de inflows y resumen
```sql
-- EP aprobados por proyecto (monto neto del período)
DROP VIEW IF EXISTS v_ep_approved_project;
CREATE VIEW v_ep_approved_project AS
SELECT h.project_id,
       strftime('%Y-%m-01', h.approved_at) AS bucket_month,
       SUM(l.amount_period) - COALESCE((SELECT SUM(d.amount) FROM ep_deductions d WHERE d.ep_id = h.id),0) AS ep_amount_net
FROM ep_headers h
JOIN ep_lines l ON l.ep_id = h.id
WHERE h.status IN ('approved','invoiced','paid')
GROUP BY h.project_id, bucket_month;

-- AR esperado (emitido no cobrado)
DROP VIEW IF EXISTS v_ar_expected_project;
CREATE VIEW v_ar_expected_project AS
SELECT a.project_id,
       strftime('%Y-%m-01', a.due_date) AS bucket_month,
       SUM(a.amount_total) - COALESCE((SELECT SUM(c.amount) FROM ar_collections c WHERE c.invoice_id = a.id),0) AS expected_inflow
FROM ar_invoices a
WHERE a.status IN ('issued')
GROUP BY a.project_id, bucket_month;

-- AR actual (cobrado)
DROP VIEW IF EXISTS v_ar_actual_project;
CREATE VIEW v_ar_actual_project AS
SELECT a.project_id,
       strftime('%Y-%m-01', c.collected_date) AS bucket_month,
       SUM(c.amount) AS actual_inflow
FROM ar_collections c
JOIN ar_invoices a ON a.id = c.invoice_id
GROUP BY a.project_id, bucket_month;
```

> **Postgres notas rápidas**: usar `DATE` y `to_char(date_trunc('month', ...),'YYYY-MM-01')` para `bucket_month`; `numeric` para montos; `generated always as identity` para PK.

---

## 2) API Flask — Boilerplate y validaciones
> Blueprint `ep_bp`. Respuestas JSON. Capturar errores con `422` (payload con `error`, `detail`, ids).

```py
# backend/ep_api.py
from flask import Blueprint, request, jsonify
import sqlite3, datetime, math

ep_bp = Blueprint('ep', __name__)
DB_PATH = 'data/chipax_data.db'  # ajustar si aplica

TAX_RATE = 0.19  # IVA ejemplo; mover a config si variable

# Helpers

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def parse_date(s):
    return datetime.date.fromisoformat(s)

class Unprocessable(ValueError):
    def __init__(self, error, detail=None, **extra):
        self.payload = {'error': error, 'detail': detail}
        self.payload.update(extra)

@ep_bp.errorhandler(Unprocessable)
def _unprocessable(e):
    return jsonify(e.payload), 422

# 2.1 GET lista EP por proyecto
@ep_bp.get('/api/projects/<int:pid>/ep')
def list_ep(pid):
    con = db()
    rows = con.execute('''
        SELECT h.*, (
            SELECT COALESCE(SUM(l.amount_period),0) FROM ep_lines l WHERE l.ep_id = h.id
        ) AS amount_period,
        (
            SELECT COALESCE(SUM(d.amount),0) FROM ep_deductions d WHERE d.ep_id = h.id
        ) AS deductions
        FROM ep_headers h
        WHERE h.project_id = ?
        ORDER BY COALESCE(h.approved_at, h.submitted_at) DESC
    ''', (pid,)).fetchall()
    return jsonify({'items': [dict(r) for r in rows]})

# 2.2 POST import EP (Excel ya parseado en front o subir file simple)
@ep_bp.post('/api/ep/import')
def import_ep():
    data = request.get_json(force=True)
    header = data.get('header')  # {project_id, contract_id?, ep_number, period_start, period_end, retention_pct}
    lines = data.get('lines', [])  # [{item_code, description, unit, qty_period, unit_price, amount_period, qty_cum, amount_cum, chapter}]
    deductions = data.get('deductions', [])  # [{type, description, amount}]

    if not header or not lines:
        raise Unprocessable('invalid_payload', 'header or lines missing')

    con = db(); cur = con.cursor()
    cur.execute('''INSERT INTO ep_headers(project_id, contract_id, ep_number, period_start, period_end, submitted_at, status, retention_pct)
                   VALUES(?,?,?,?,?, date('now'), 'submitted', ?)''',
                (header['project_id'], header.get('contract_id'), header.get('ep_number'), header.get('period_start'), header.get('period_end'), header.get('retention_pct')))
    ep_id = cur.lastrowid

    # Validación contra contrato/SOV si existe
    if header.get('contract_id'):
        # Mapa item_code -> (line_total, amount_cum_prev)
        sov = { r['item_code']: r for r in con.execute('SELECT i.item_code, i.line_total FROM client_sov_items i WHERE i.contract_id=?', (header['contract_id'],)) }
        # acumulado previo por item
        prev = { r['item_code']: r['amount_cum'] for r in con.execute('''
            SELECT l.item_code, COALESCE(SUM(l.amount_period),0) AS amount_cum
            FROM ep_lines l JOIN ep_headers h ON h.id=l.ep_id
            WHERE h.contract_id=? AND h.status IN('approved','invoiced','paid')
            GROUP BY l.item_code
        ''', (header['contract_id'],)) }
    else:
        sov, prev = {}, {}

    for ln in lines:
        amt = ln.get('amount_period')
        if amt is None and ln.get('qty_period') is not None and ln.get('unit_price') is not None:
            amt = float(ln['qty_period']) * float(ln['unit_price'])
        # regla EP ≤ SOV (si hay contrato)
        code = ln.get('item_code')
        if code in sov:
            cap = float(sov[code]['line_total'])
            prev_amt = float(prev.get(code, 0))
            if prev_amt + (amt or 0) > cap + 1e-6:
                raise Unprocessable('ep_exceeds_contract_item', f'Item {code} excede SOV', item_code=code, cap=cap, prev=prev_amt, attempt=amt)
        cur.execute('''INSERT INTO ep_lines(ep_id, sov_item_id, item_code, description, unit, qty_period, unit_price, amount_period, qty_cum, amount_cum, chapter)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                    (ep_id, ln.get('sov_item_id'), code, ln.get('description'), ln.get('unit'), ln.get('qty_period'), ln.get('unit_price'), amt, ln.get('qty_cum'), ln.get('amount_cum'), ln.get('chapter')))

    for d in deductions:
        cur.execute('INSERT INTO ep_deductions(ep_id, type, description, amount) VALUES(?,?,?,?)',
                    (ep_id, d.get('type'), d.get('description'), d.get('amount')))

    con.commit()
    return jsonify({'ok': True, 'ep_id': ep_id})

# 2.3 POST approve EP
@ep_bp.post('/api/ep/<int:ep_id>/approve')
def approve_ep(ep_id):
    con = db(); cur = con.cursor()
    cur.execute('SELECT status FROM ep_headers WHERE id=?', (ep_id,))
    row = cur.fetchone()
    if not row: raise Unprocessable('not_found', 'EP inexistente', ep_id=ep_id)
    if row['status'] not in ('draft','submitted'):
        raise Unprocessable('invalid_state', f"No se puede aprobar desde {row['status']}")
    cur.execute("UPDATE ep_headers SET status='approved', approved_at=date('now') WHERE id=?", (ep_id,))
    con.commit()
    return jsonify({'ok': True, 'ep_id': ep_id, 'status': 'approved'})

# 2.4 POST generate invoice from EP
@ep_bp.post('/api/ep/<int:ep_id>/generate-invoice')
def ep_to_invoice(ep_id):
    con = db(); cur = con.cursor()
    h = con.execute('SELECT * FROM ep_headers WHERE id=?', (ep_id,)).fetchone()
    if not h: raise Unprocessable('not_found', 'EP inexistente', ep_id=ep_id)
    if h['status'] not in ('approved','invoiced','paid'):
        raise Unprocessable('invalid_state', 'EP debe estar aprobado')
    sums = con.execute('''SELECT COALESCE(SUM(l.amount_period),0) AS amt FROM ep_lines l WHERE l.ep_id=?''', (ep_id,)).fetchone()
    ded = con.execute('''SELECT COALESCE(SUM(d.amount),0) AS ded FROM ep_deductions d WHERE d.ep_id=?''', (ep_id,)).fetchone()
    net = float(sums['amt']) - float(ded['ded'])
    tax = round(net * TAX_RATE, 2)
    total = net + tax

    # calcular due_date por términos (contrato->customer)
    terms = h['retention_pct']  # MAL ejemplo; en real: lookup payment_terms_days desde client_contracts/customer
    payment_terms_days = con.execute('SELECT COALESCE(payment_terms_days,30) AS d FROM client_contracts WHERE id=?', (h['contract_id'],)).fetchone()
    days = int(payment_terms_days['d']) if payment_terms_days else 30
    cur.execute('''INSERT INTO ar_invoices(project_id, customer_id, ep_id, invoice_number, invoice_date, due_date, amount_net, tax_amount, amount_total, status)
                   VALUES(?,?,?,?, date('now'), date('now','+'||?||' day'), ?, ?, ?, 'issued')''',
                (h['project_id'], 0, ep_id, None, days, net, tax, total))
    inv_id = cur.lastrowid
    cur.execute("UPDATE ep_headers SET status='invoiced' WHERE id=?", (ep_id,))
    con.commit()
    return jsonify({'ok': True, 'invoice_id': inv_id, 'amount_net': net, 'tax_amount': tax, 'amount_total': total})
```

> **Notas**: reemplazar `customer_id` real, `invoice_number` según numeración; si ya existe factura para ese EP, retornar 422 `duplicate_invoice`.

**Registro del blueprint en el server:**
```py
# backend/server.py
from ep_api import ep_bp
app.register_blueprint(ep_bp)
```

---

## 3) Frontend — Wizard de Importación EP (Next.js + TS)
> Estilo: Inter, bordes 1px, radius 2xl, sin sombras. 3 pasos: **Subir**, **Mapear**, **Revisar & Guardar**.

### 3.1 Cliente API
```ts
// frontend/lib/epApi.ts
const API = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:5555/api';

export async function listEP(projectId: number){
  const r = await fetch(`${API}/projects/${projectId}/ep`, { cache: 'no-store' });
  if(!r.ok) throw new Error('list ep failed');
  return r.json();
}

export async function importEP(payload: any){
  const r = await fetch(`${API}/ep/import`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  if(!r.ok){ const e = await r.json(); throw new Error(e.detail || e.error || 'import failed'); }
  return r.json();
}

export async function approveEP(epId: number){
  const r = await fetch(`${API}/ep/${epId}/approve`, { method:'POST' });
  if(!r.ok){ const e = await r.json(); throw new Error(e.detail || e.error || 'approve failed'); }
  return r.json();
}

export async function generateInvoiceFromEP(epId: number){
  const r = await fetch(`${API}/ep/${epId}/generate-invoice`, { method:'POST' });
  if(!r.ok){ const e = await r.json(); throw new Error(e.detail || e.error || 'invoice failed'); }
  return r.json();
}
```

### 3.2 Wizard (componente client)
```tsx
// frontend/app/proyectos/[id]/ventas-ep/import/page.tsx
'use client';
import React, { useState } from 'react';
import * as XLSX from 'xlsx';
import { importEP } from '@/lib/epApi';

const SUGGEST = {
  ep_number: ['N EP','EP','N_Estado'],
  period_start: ['Desde','Inicio'],
  period_end: ['Hasta','Termino'],
  item_code: ['Código','Item','Ítem'],
  description: ['Descripción','Desc'],
  unit: ['Unidad','UM'],
  qty_period: ['Cant Mes','Cant'],
  unit_price: ['PU','Precio Unitario'],
  amount_period: ['Monto Mes','Monto'],
  qty_cum: ['Cant Acum'],
  amount_cum: ['Monto Acum'],
  chapter: ['Capítulo','Capitulo']
};

export default function ImportEPPage(){
  const [projectId, setProjectId] = useState<number | null>(null);
  const [raw, setRaw] = useState<any[]>([]);
  const [map, setMap] = useState<Record<string,string>>({});
  const [header, setHeader] = useState<any>({});
  const [preview, setPreview] = useState<any[]>([]);
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);

  function onFile(e:any){
    const f = e.target.files?.[0];
    if(!f) return;
    const reader = new FileReader();
    reader.onload = () => {
      const wb = XLSX.read(reader.result, { type:'binary' });
      const ws = wb.Sheets[wb.SheetNames[0]];
      const json = XLSX.utils.sheet_to_json(ws, { defval: '' });
      setRaw(json as any[]);
      setStep(2);
    };
    reader.readAsBinaryString(f);
  }

  function autoMap(headers: string[]){
    const m: Record<string,string> = {};
    for(const k of Object.keys(SUGGEST)){
      const candidates = (SUGGEST as any)[k] as string[];
      const hit = headers.find(h => candidates.some(c => h.toLowerCase().includes(c.toLowerCase())));
      if(hit) m[k] = hit;
    }
    setMap(m);
  }

  function buildPreview(){
    const rows = raw.map((r:any) => ({
      item_code: r[map.item_code] ?? '',
      description: r[map.description] ?? '',
      unit: r[map.unit] ?? '',
      qty_period: parseFloat(r[map.qty_period]) || 0,
      unit_price: parseFloat(r[map.unit_price]) || 0,
      amount_period: parseFloat(r[map.amount_period]) || undefined,
      qty_cum: parseFloat(r[map.qty_cum]) || undefined,
      amount_cum: parseFloat(r[map.amount_cum]) || undefined,
      chapter: r[map.chapter] ?? ''
    }));
    setPreview(rows);
  }

  async function submit(){
    setBusy(true);
    try{
      const payload = { header: { project_id: projectId, ...header }, lines: preview, deductions: [] };
      const resp = await importEP(payload);
      alert(`EP creado #${resp.ep_id}`);
      setStep(1); setRaw([]); setPreview([]);
    }catch(e:any){ alert(e.message || 'Error'); }
    finally{ setBusy(false); }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <h1 className="text-2xl font-semibold">Importar Estado de Pago (Cliente)</h1>

      {step===1 && (
        <div className="rounded-2xl border p-4 space-y-3">
          <div className="text-sm text-neutral-600">1) Selecciona Proyecto y sube el Excel aprobado por el cliente.</div>
          <input type="number" placeholder="Project ID" className="border p-2 rounded" onChange={e=>setProjectId(parseInt(e.target.value))} />
          <input type="file" accept=".xlsx,.xls,.csv" onChange={onFile} />
        </div>
      )}

      {step===2 && (
        <div className="rounded-2xl border p-4 space-y-3">
          <div className="text-sm text-neutral-600">2) Mapea columnas</div>
          <button className="border px-3 py-1 rounded" onClick={()=>autoMap(Object.keys(raw[0]||{}))}>Auto-mapear</button>
          <div className="grid grid-cols-2 gap-2">
            {Object.keys(SUGGEST).map(k => (
              <div key={k} className="flex items-center gap-2">
                <label className="w-40 text-sm text-neutral-500">{k}</label>
                <select className="border p-1 rounded flex-1" value={map[k]||''} onChange={e=>setMap({...map,[k]:e.target.value})}>
                  <option value="">--</option>
                  {Object.keys(raw[0]||{}).map(h => <option key={h} value={h}>{h}</option>)}
                </select>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-3 gap-2">
            <input className="border p-2 rounded" placeholder="EP Number" onChange={e=>setHeader({...header, ep_number:e.target.value})} />
            <input className="border p-2 rounded" placeholder="Desde (YYYY-MM-DD)" onChange={e=>setHeader({...header, period_start:e.target.value})} />
            <input className="border p-2 rounded" placeholder="Hasta (YYYY-MM-DD)" onChange={e=>setHeader({...header, period_end:e.target.value})} />
          </div>
          <button className="border px-3 py-1 rounded" onClick={()=>{ buildPreview(); setStep(3); }}>Continuar</button>
        </div>
      )}

      {step===3 && (
        <div className="rounded-2xl border p-4 space-y-3">
          <div className="text-sm text-neutral-600">3) Revisión & Guardar</div>
          <div className="max-h-64 overflow-auto border rounded">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-neutral-500">
                  {['item_code','description','unit','qty_period','unit_price','amount_period','qty_cum','amount_cum','chapter'].map(k=> <th key={k} className="p-2">{k}</th>)}
                </tr>
              </thead>
              <tbody>
                {preview.map((r,i)=> (
                  <tr key={i} className="border-t">
                    <td className="p-2">{r.item_code}</td>
                    <td className="p-2">{r.description}</td>
                    <td className="p-2">{r.unit}</td>
                    <td className="p-2">{r.qty_period}</td>
                    <td className="p-2">{r.unit_price}</td>
                    <td className="p-2">{r.amount_period ?? (r.qty_period*r.unit_price).toFixed(2)}</td>
                    <td className="p-2">{r.qty_cum ?? ''}</td>
                    <td className="p-2">{r.amount_cum ?? ''}</td>
                    <td className="p-2">{r.chapter}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button disabled={busy} className="border px-3 py-1 rounded" onClick={submit}>{busy?'Guardando…':'Guardar EP'}</button>
        </div>
      )}
    </div>
  );
}
```

---

## 4) Integración con Módulo Proyecto / Cashflow
- Incluir en `/api/projects/:id/finance` los arrays:
  - `ep_pending_invoice` (EP aprobados sin factura): query por `ep_headers.status='approved'`.
  - `ar_from_ep` (facturas emitidas desde EP) y `collections`.
- En **cashflow**: sumar `v_ar_expected_project` como **inflows expected**; `v_ar_actual_project` como **inflows actual**.
- En la página Proyecto ▸ **Ventas/EP**: mostrar backlog por cobrar (facturas emitidas no cobradas) y aging.

---

## 5) Validaciones críticas (server-side)
- **EP ≤ SOV** por ítem (si hay contrato). Error 422 `ep_exceeds_contract_item` con `{item_code, cap, prev, attempt}`.
- **Factura ≤ EP** al generar factura. Error 422 `invoice_over_ep`.
- **Cobro ≤ Factura** al registrar cobranzas. Error 422 `over_collected`.
- **Fechas** ISO y positivas; montos no negativos.

---

## 6) Roadmap de cierre (rápido)
1) Conectar endpoints en server principal y proteger con auth/roles.  
2) Agregar link a **Drive** en `ep_files` y preview en UI.  
3) Agregar botón **Generar factura** en tabla EP y CTA de cobro (WhatsApp con plantilla).  
4) Extender a **retenciones** (ledger y liberación).  
5) Postgres flavor (migración y vistas).

