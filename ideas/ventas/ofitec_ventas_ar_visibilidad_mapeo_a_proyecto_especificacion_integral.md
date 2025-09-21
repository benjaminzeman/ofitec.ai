# OFITEC — **Ventas (AR)** Visibilidad + **Mapeo a Proyecto** (Especificación integral)
> Objetivo: que **veas todas tus Facturas de Venta** y que Ofitec **asigne (o sugiera)** el proyecto correcto automáticamente (con explicaciones), aprovechando conciliaciones históricas de Chipax y cumpliendo *docs_oficiales* (Ley de Puertos UI 3001 + API 5555, DB Canónica, vistas `v_*`).

---

## 0) Contexto y metas
- Hoy la vista de **Ventas** aparece vacía o pobremente poblada. 
- Además, muchas facturas **no tienen proyecto** asignado → el tablero financiero pierde valor.
- Este documento entrega **todo lo necesario** para: 
  1) **Importar y mostrar** ventas reales (desde Chipax hoy, SII mañana),
  2) **Sugerir/auto-asignar** el proyecto de cada factura con **explicabilidad** y **aprendizaje**,
  3) Dejar **endpoints** y **UI** listos para pegar.

---

## 1) Diagnóstico rápido: por qué no ves Ventas
### 1.1 Chequeos SQL inmediatos
```sql
-- ¿Hay ventas en la tabla canónica?
SELECT COUNT(*) AS n FROM sales_invoices;
SELECT * FROM sales_invoices LIMIT 5;

-- ¿Están todas sin proyecto?
SELECT COUNT(*) AS sin_proyecto
FROM sales_invoices WHERE project_id IS NULL;

-- ¿La vista/endpoint están apuntando a otra cosa?
-- (Asegurarse de usar v_facturas_venta basada en sales_invoices)
```

### 1.2 Causas típicas
1) **No se importaron** las ventas (Chipax/SII) → crear importador AR.
2) La UI llama a un **endpoint distinto** o vista proxy → crear/usar `v_facturas_venta` (abajo) y endpoint `/api/sales_invoices`.
3) **Filtros** por defecto (fecha/proyecto) ocultan resultados → habilitar `date_from/date_to` y `project_id` **opcionales**.

---

## 2) Modelo de datos canónico (mínimamente invasivo)
> Si ya existe `sales_invoices`, sólo **agrega columnas** faltantes con `ALTER TABLE IF NOT EXISTS` o ignora las de más.

```sql
-- Facturas de Venta (AR)
CREATE TABLE IF NOT EXISTS sales_invoices (
  id INTEGER PRIMARY KEY,
  customer_rut TEXT,
  customer_name TEXT,
  invoice_number TEXT,     -- folio
  issue_date TEXT,         -- YYYY-MM-DD
  due_date TEXT,
  currency TEXT DEFAULT 'CLP',
  net_amount REAL,
  tax_amount REAL,
  exempt_amount REAL,
  total_amount REAL,
  status TEXT,             -- open|paid|overdue|cancelled
  project_id INTEGER,      -- nullable (a asignar)
  source_platform TEXT,    -- CHIPAX|SII|...
  source_id TEXT,          -- id externo
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Reglas y eventos para mapeo AR→Proyecto
CREATE TABLE IF NOT EXISTS ar_project_rules (
  id INTEGER PRIMARY KEY,
  rule_type TEXT CHECK(rule_type IN ('client_rut','alias_regex','contract_ref','drive_path','date_window')) NOT NULL,
  client_rut TEXT,
  project_id INTEGER,
  pattern TEXT,              -- regex/alias/código contrato
  valid_from TEXT, valid_to TEXT,
  confidence REAL DEFAULT 0.8,
  hits INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ar_map_events (
  id INTEGER PRIMARY KEY,
  invoice_id INTEGER NOT NULL,
  candidates_json TEXT NOT NULL,
  chosen_project_id INTEGER,
  confidence REAL,
  reasons TEXT,
  accepted INTEGER,          -- 1|0
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  user_id TEXT
);
```

**Conciliación (reutiliza recon_\*)**
```sql
-- Si aún no existen, usar las definidas en Conciliación Parte 2
CREATE TABLE IF NOT EXISTS recon_reconciliations (
  id INTEGER PRIMARY KEY,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  context TEXT CHECK(context IN ('bank','sales','purchase','expense','payroll','tax')) NOT NULL,
  confidence REAL,
  user_id TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS recon_links (
  id INTEGER PRIMARY KEY,
  reconciliation_id INTEGER NOT NULL REFERENCES recon_reconciliations(id) ON DELETE CASCADE,
  bank_movement_id INTEGER,
  sales_invoice_id INTEGER,
  ap_invoice_id INTEGER,
  expense_id INTEGER,
  payroll_id INTEGER,
  tax_id INTEGER,
  amount REAL NOT NULL
);
```

**Índices útiles**
```sql
CREATE INDEX IF NOT EXISTS idx_si_issue_date ON sales_invoices(issue_date);
CREATE INDEX IF NOT EXISTS idx_si_customer ON sales_invoices(customer_rut);
CREATE INDEX IF NOT EXISTS idx_si_project ON sales_invoices(project_id);
CREATE INDEX IF NOT EXISTS idx_rl_sales ON recon_links(sales_invoice_id);
```

---

## 3) Importador AR (Chipax hoy; SII mañana)
Archivo sugerido: `tools/import_chipax_ar.py`

### 3.1 Mapeo columnas Chipax → `sales_invoices`
| Chipax CSV                         | sales_invoices              |
|-----------------------------------|-----------------------------|
| RUT                                | customer_rut                |
| Razón Social                       | customer_name               |
| Folio                              | invoice_number              |
| Fecha Emisión                      | issue_date                  |
| Fecha Vencimiento                  | due_date                    |
| Moneda / TC                        | currency                    |
| Monto Neto (CLP)                   | net_amount                  |
| Monto Exento (CLP)                 | exempt_amount               |
| Monto IVA (CLP)                    | tax_amount                  |
| Monto Total (CLP)                  | total_amount                |
| (constante)                        | source_platform = 'CHIPAX'  |

- Reutilizar `etl_common.py` (normalización números con coma/punto). 
- A futuro (SII): agregar lector XML/JSON y mapear a las mismas columnas.

### 3.2 Pagos (conciliación AR)
- Si el CSV de Chipax trae referencia al **movimiento bancario** (fecha, monto, banco, glosa), crear `recon_reconciliations(context='sales')` y `recon_links(sales_invoice_id↔bank_movement_id)`.
- Tolerancia de match: ±1% o ±$1.

---

## 4) Vistas canónicas para la UI
### 4.1 `v_facturas_venta`
```sql
DROP VIEW IF EXISTS v_facturas_venta;
CREATE VIEW v_facturas_venta AS
SELECT id                 AS invoice_id,
       customer_rut,
       customer_name,
       invoice_number,
       issue_date,
       due_date,
       currency,
       net_amount,
       tax_amount,
       exempt_amount,
       total_amount,
       COALESCE(status,'open') AS status,
       project_id,
       COALESCE(source_platform,'unknown') AS source
FROM sales_invoices;
```

### 4.2 `v_ar_payments` (cobros conciliados)
```sql
DROP VIEW IF EXISTS v_ar_payments;
CREATE VIEW v_ar_payments AS
SELECT rl.sales_invoice_id AS invoice_id,
       SUM(rl.amount)      AS paid_amount
FROM recon_links rl
JOIN recon_reconciliations rr ON rr.id = rl.reconciliation_id AND rr.context='sales'
GROUP BY rl.sales_invoice_id;
```

### 4.3 `v_sales_invoices_with_project` (enriquecida)
```sql
DROP VIEW IF EXISTS v_sales_invoices_with_project;
CREATE VIEW v_sales_invoices_with_project AS
SELECT v.*, COALESCE(paid.paid_amount,0) AS paid_amount,
       CASE WHEN COALESCE(paid.paid_amount,0) >= v.total_amount THEN 1 ELSE 0 END AS fully_paid
FROM v_facturas_venta v
LEFT JOIN v_ar_payments paid ON paid.invoice_id = v.invoice_id;
```

### 4.4 (Opcional) `v_ar_aging_by_project`
```sql
DROP VIEW IF EXISTS v_ar_aging_by_project;
CREATE VIEW v_ar_aging_by_project AS
SELECT COALESCE(s.project_id, -1) AS project_id,
       SUM(CASE WHEN julianday('now') - julianday(s.due_date) BETWEEN 1 AND 30 THEN s.total_amount - COALESCE(p.paid_amount,0) ELSE 0 END) AS d1_30,
       SUM(CASE WHEN julianday('now') - julianday(s.due_date) BETWEEN 31 AND 60 THEN s.total_amount - COALESCE(p.paid_amount,0) ELSE 0 END) AS d31_60,
       SUM(CASE WHEN julianday('now') - julianday(s.due_date) > 60 THEN s.total_amount - COALESCE(p.paid_amount,0) ELSE 0 END) AS d60_plus
FROM sales_invoices s
LEFT JOIN v_ar_payments p ON p.invoice_id = s.id
GROUP BY COALESCE(s.project_id, -1);
```

---

## 5) Endpoints 5555 (API) 
### 5.1 Lista de facturas de venta
```py
# backend/api_sales_invoices.py
from flask import Blueprint, request, jsonify
import sqlite3

bp = Blueprint('sales', __name__)
DB = 'data/chipax_data.db'

def db():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; return con

@bp.get('/api/sales_invoices')
def list_sales():
    page = int(request.args.get('page',1)); per = int(request.args.get('per_page',50))
    df = request.args.get('date_from','2000-01-01'); dt = request.args.get('date_to','2100-01-01')
    proj = request.args.get('project_id')
    base = "FROM v_sales_invoices_with_project WHERE issue_date BETWEEN ? AND ?"
    params=[df,dt]
    if proj: base += " AND project_id = ?"; params.append(int(proj))
    con = db(); cur=con.cursor()
    cur.execute(f"SELECT COUNT(1) AS n {base}", params); total = cur.fetchone()['n']
    cur.execute(f"SELECT * {base} ORDER BY issue_date DESC LIMIT ? OFFSET ?", params+[per,(page-1)*per])
    rows=[dict(x) for x in cur.fetchall()]
    return jsonify({'items':rows,'page_context':{'page':page,'per_page':per,'total':total,'has_more_page': page*per<total}})
```
> Registrar en `server.py`: `from api_sales_invoices import bp as sales_bp; app.register_blueprint(sales_bp)`.

### 5.2 Sugerencias de proyecto (AR→Proyecto)
```py
# backend/api_ar_map.py
from flask import Blueprint, request, jsonify
import sqlite3, re, json

bp = Blueprint('armap', __name__)
DB = 'data/chipax_data.db'

def db():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; return con

@bp.post('/api/ar-map/suggestions')
def ar_suggestions():
    b = request.get_json(force=True)
    inv_id = b.get('invoice_id'); amount = float(b.get('amount',0)); date = b.get('date'); rut = b.get('customer_rut')
    name = b.get('customer_name','') or ''
    invoice_number = b.get('invoice_number','') or ''
    if not inv_id or not amount or not date:
        return jsonify({'error':'invalid_payload','detail':'invoice_id, amount, date requeridos'}), 422
    con = db(); cur=con.cursor()

    # 1) Cliente con un sólo proyecto activo
    cur.execute('''
      SELECT p.id AS project_id, p.name AS project_name
      FROM projects p
      JOIN projects_customers pc ON pc.project_id = p.id
      WHERE pc.customer_rut = ? AND p.status='active'
    ''', (rut,))
    rows = [dict(r) for r in cur.fetchall()]
    items=[]
    if len(rows)==1:
        items.append({'project_id': rows[0]['project_id'], 'project_name': rows[0]['project_name'], 'confidence': 0.95, 'reasons': ['cliente único activo']})

    # 2) EP del mes ±2% (si existe vista)
    try:
        cur.execute('''
          SELECT ep.project_id, pr.name AS project_name
          FROM v_ep_resumen ep JOIN projects pr ON pr.id = ep.project_id
          WHERE ep.customer_rut = ? AND ABS(ep.monto_mes - ?) <= ?*0.02
        ''',(rut, amount, amount))
        for r in cur.fetchall():
            items.append({'project_id': r['project_id'], 'project_name': r['project_name'], 'confidence': 0.92, 'reasons': ['monto≈EP mes','misma contraparte']})
    except Exception:
        pass

    # 3) Alias regex (reglas aprendidas)
    cur.execute("SELECT project_id, pattern, confidence FROM ar_project_rules WHERE rule_type='alias_regex'")
    for r in cur.fetchall():
        try:
            if re.search(r['pattern'], (name+' '+invoice_number), re.I):
                items.append({'project_id': r['project_id'], 'project_name': None, 'confidence': float(r['confidence']), 'reasons': [f"alias:'{r['pattern']}'"]})
        except Exception:
            continue

    # 4) Pagos conciliados (heredar proyecto si el cobro está vinculado)
    cur.execute('''
      SELECT rl.bank_movement_id, pm.project_id
      FROM recon_links rl
      JOIN payments_meta pm ON pm.bank_movement_id = rl.bank_movement_id
      WHERE rl.sales_invoice_id = ?
    ''',(inv_id,))
    for r in cur.fetchall():
        if r['project_id'] is not None:
            items.append({'project_id': r['project_id'], 'project_name': None, 'confidence': 0.9, 'reasons': ['heredado de cobro conciliado']})

    # ordena y agrega nombres
    seen=set(); out=[]
    for it in sorted(items, key=lambda x: x['confidence'], reverse=True):
        pid = it['project_id']
        if pid in seen: continue
        seen.add(pid)
        if not it.get('project_name'):
            cur.execute('SELECT name FROM projects WHERE id=?',(pid,)); row=cur.fetchone()
            it['project_name'] = row['name'] if row else f'Project {pid}'
        out.append(it)
    return jsonify({'items': out[:5]})

@bp.post('/api/ar-map/confirm')
def ar_confirm():
    b = request.get_json(force=True)
    inv_id = b.get('invoice_id'); pid = b.get('project_id'); conf = float(b.get('confidence',0)); reasons = b.get('reasons') or []
    if not inv_id or not pid:
        return jsonify({'error':'invalid_payload','detail':'invoice_id y project_id requeridos'}), 422
    con = db(); cur=con.cursor()
    cur.execute('UPDATE sales_invoices SET project_id=? WHERE id=?',(pid,inv_id))
    cur.execute('INSERT INTO ar_map_events(invoice_id, candidates_json, chosen_project_id, confidence, reasons, accepted, user_id) VALUES(?,?,?,?,?,1,?)', (
        inv_id, b.get('candidates_json','[]'), pid, conf, ','.join(reasons), b.get('metadata',{}).get('user_id')
    ))
    con.commit()
    return jsonify({'ok':True})
```
> Registrar en `server.py`: `from api_ar_map import bp as armap_bp; app.register_blueprint(armap_bp)`.

---

## 6) UI (Next.js/Tailwind) — Lista de ventas + Drawer “Asignar proyecto”
### 6.1 Lista (resumen)
```tsx
// app/ventas/page.tsx
'use client';
import { useEffect, useState } from 'react';
import AssignProjectDrawer from '@/components/AssignProjectDrawer';

export default function Ventas(){
  const [rows, setRows] = useState<any[]>([]);
  const [sel, setSel] = useState<any|null>(null);
  useEffect(()=>{(async()=>{
    const r = await fetch('http://localhost:5555/api/sales_invoices?page=1&per_page=50');
    const j = await r.json(); setRows(j.items||[]);
  })();},[]);
  return (
    <div className="p-4">
      <h1 className="text-xl font-semibold mb-3">Facturas de Venta</h1>
      <div className="rounded-2xl border overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-neutral-500">
              <th className="p-2">Folio</th>
              <th className="p-2">Cliente</th>
              <th className="p-2">Fecha</th>
              <th className="p-2">Total</th>
              <th className="p-2">Proyecto</th>
              <th className="p-2">Cobrado</th>
              <th className="p-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(x=> (
              <tr key={x.invoice_id} className="border-t">
                <td className="p-2">{x.invoice_number}</td>
                <td className="p-2">{x.customer_name}</td>
                <td className="p-2">{x.issue_date}</td>
                <td className="p-2">{Number(x.total_amount).toLocaleString()}</td>
                <td className="p-2">{x.project_id ? x.project_id : <span className="text-amber-600">(sin proyecto)</span>}</td>
                <td className="p-2">{Number(x.paid_amount||0).toLocaleString()}</td>
                <td className="p-2">
                  {!x.project_id && <button className="border px-2 py-1 rounded" onClick={()=>setSel(x)}>Asignar proyecto</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {sel && <AssignProjectDrawer invoice={sel} onClose={()=>setSel(null)} />}
    </div>
  );
}
```

### 6.2 Drawer de asignación
```tsx
// components/AssignProjectDrawer.tsx
'use client';
import { useEffect, useState } from 'react';

export default function AssignProjectDrawer({ invoice, onClose }:{ invoice:any; onClose:()=>void }){
  const [items, setItems] = useState<any[]>([]);
  const [picked, setPicked] = useState<any|null>(null);
  useEffect(()=>{(async()=>{
    const r = await fetch('http://localhost:5555/api/ar-map/suggestions',{
      method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({
        invoice_id: invoice.invoice_id, amount: invoice.total_amount, date: invoice.issue_date,
        customer_rut: invoice.customer_rut, customer_name: invoice.customer_name, invoice_number: invoice.invoice_number
      })});
    const j = await r.json(); setItems(j.items||[]);
  })();},[invoice.invoice_id]);

  async function confirm(){
    if(!picked) return;
    const r = await fetch('http://localhost:5555/api/ar-map/confirm',{
      method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({
        invoice_id: invoice.invoice_id, project_id: picked.project_id, confidence: picked.confidence,
        reasons: picked.reasons, metadata: { user_id: 'me' }
      })});
    const j = await r.json(); if(j.ok){ onClose(); }
  }

  return (
    <div className="fixed inset-y-0 right-0 w-[420px] bg-white border-l p-4 z-50 overflow-auto">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-semibold">Asignar proyecto</h3>
        <button className="text-sm" onClick={onClose}>Cerrar</button>
      </div>
      <div className="text-sm text-neutral-600 mb-2">{invoice.customer_name} • {invoice.invoice_number} • {Number(invoice.total_amount).toLocaleString()}</div>
      <div className="space-y-2">
        {items.map((it:any,idx:number)=> (
          <div key={idx} className={`rounded-2xl border p-3 ${picked===it?'ring-1':''}`}>
            <div className="flex items-center justify-between">
              <div className="font-medium">{it.project_name}</div>
              <div className="text-xs">conf {(it.confidence*100).toFixed(1)}%</div>
            </div>
            <div className="text-xs text-neutral-500 mt-1">{(it.reasons||[]).join(' • ')}</div>
            <div className="mt-2 flex gap-2">
              <button className="border px-2 py-1 rounded" onClick={()=>setPicked(it)}>Elegir</button>
              {idx===0 && <button className="border px-2 py-1 rounded" onClick={()=>{setPicked(it); confirm();}}>Aceptar #1</button>}
            </div>
          </div>
        ))}
        {(!items || items.length===0) && <div className="text-xs text-neutral-500">Sin sugerencias. Busca manualmente…</div>}
      </div>
      {picked && <div className="mt-3 flex gap-2">
        <button className="border px-3 py-1 rounded" onClick={confirm}>Confirmar</button>
      </div>}
    </div>
  );
}
```

---

## 7) Algoritmo de sugerencias (explicable y ampliable)
**Generación de candidatos** (en este orden):
1) **Cliente único activo** en esa fecha → proyecto directo (conf 0.95).
2) **EP del mes** (monto≈factura ±2%) → proyecto candidato (0.92).
3) **Alias regex** (reglas aprendidas): patrón en `customer_name`/`invoice_number` (0.88 default).
4) **Cobro conciliado** con proyecto inferido (0.90).
5) **Ruta de Drive** (si disponible): carpeta de proyecto (0.9–0.95).

**Ranking/pesos**: ordenar por `confidence` y **mostrar razones**. 
**Umbrales**: `auto ≥ 0.97` (opcional), `one-click ≥ 0.92`, `review < 0.92`.
**Aprendizaje**: cada confirmación inserta en `ar_map_events`; una tarea batch puede promover patrones frecuentes a `ar_project_rules` y subir `confidence`.

---

## 8) QA / Queries útiles
```sql
-- ¿Cuántas ventas importadas?
SELECT COUNT(*) FROM sales_invoices;

-- ¿Cuántas sin proyecto?
SELECT COUNT(*) FROM sales_invoices WHERE project_id IS NULL;

-- ¿Cobrado por factura (conciliado)?
SELECT * FROM v_sales_invoices_with_project WHERE fully_paid=1 LIMIT 10;

-- Aging resumido por proyecto
SELECT * FROM v_ar_aging_by_project;
```

---

## 9) Seed mínimo (demo rápida)
```sql
INSERT INTO projects(id,name,status) VALUES (100,'PROY-100 Centro Logístico','active') ON CONFLICT DO NOTHING;
INSERT INTO projects(id,name,status) VALUES (101,'PROY-101 Clínica Norte','active') ON CONFLICT DO NOTHING;

INSERT INTO sales_invoices(id,customer_rut,customer_name,invoice_number,issue_date,due_date,total_amount,status,source_platform)
VALUES (7001,'76.543.210-K','MegaCliente S.A.','FV-1001','2025-08-30','2025-09-30',25369786,'open','CHIPAX');

-- Regla alias: todo lo que diga "Centro Logístico" → PROY-100
INSERT INTO ar_project_rules(rule_type, client_rut, project_id, pattern, confidence)
VALUES('alias_regex',NULL,100,'CENTRO\s+LOGISTICO',0.9);
```

---

## 10) Rollout plan (paso a paso para Copilot)
1) **DDL**: asegurar `sales_invoices`, `ar_project_rules`, `ar_map_events`, índices.
2) **Importador AR** desde Chipax (CSV) → poblar `sales_invoices` y, si es posible, crear `recon_*` para cobros.
3) **Vistas**: crear `v_facturas_venta`, `v_ar_payments`, `v_sales_invoices_with_project`, `v_ar_aging_by_project`.
4) **Endpoints**: montar `/api/sales_invoices` y `/api/ar-map/*`.
5) **UI**: página de ventas + `AssignProjectDrawer` con botón “Asignar proyecto”.
6) **QA**: queries de §8, y prueba manual con el seed de §9.
7) **Mejoras**: tarea batch para promover reglas (regex aprendidas), incorporar señal de Drive y EP si aún no está.

---

## 11) Notas de cumplimiento (*docs_oficiales*)
- **Ley de Puertos**: UI 3001 consume API 5555; no se consulta la DB directamente desde el frontend.
- **DB Canónica**: toda consulta desde vistas `v_*`; las inserciones/updates con endpoints.
- **Explicabilidad**: cada sugerencia muestra `reasons`; `ar_map_events` conserva el rastro de decisión.
- **No ruptura**: las vistas nuevas no reemplazan contratos existentes; si existe una `v_facturas_venta`, alinear columnas.

---

## 12) Extensiones futuras
- Integración **SII**: lector XML/JSON y normalización a `sales_invoices`.
- **Auto‑asignación segura** con notificación si `confidence ≥ umbral` y sin conflictos.
- Detec. de **EP** en PDF/Excel con OCR y heurísticas de subtotales.
- Reportes de **margen por proyecto** en tiempo real (Ventas − AP Facturado), ya enlazado al tablero **Control Financiero 360**.

---

### Cierre
Con este paquete:
- La vista de Ventas **se llena** correctamente.
- Cada factura **obtiene** un proyecto sugerido (o asignación 1‑click) con **razones**.
- Aumenta la calidad del **Control Financiero 360** (margen, aging, cobranzas) sin procesos manuales.
- Todo queda **alineado** a la arquitectura de Ofitec (vistas canónicas + API 5555 + UI 3001).