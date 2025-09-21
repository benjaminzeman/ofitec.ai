# OFITEC — Conciliación: **Snippets Implementables** (Parte 2)
> Segunda parte para evitar límites de tamaño. Incluye **código listo** para pegar: DDL + migraciones, endpoints Flask (`/sugerencias`, `/preview`, `/confirmar`), *adapter* al motor inteligente, normalización/índices, cliente TS y **ReconcileDrawer** (UI) + componentes.

---

## 1) SQL — DDL/Migraciones (SQLite y Postgres)

### 1.1 SQLite (migración idempotente)
```sql
-- migrations/20250914_recon_tables.sql
PRAGMA foreign_keys=ON;

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
  reconciliation_id INTEGER NOT NULL,
  bank_movement_id INTEGER,
  sales_invoice_id INTEGER,
  purchase_invoice_id INTEGER,
  expense_id INTEGER,
  payroll_id INTEGER,
  tax_id INTEGER,
  amount REAL NOT NULL,
  FOREIGN KEY(reconciliation_id) REFERENCES recon_reconciliations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recon_training_events (
  id INTEGER PRIMARY KEY,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  context TEXT,
  source_json TEXT NOT NULL,
  chosen_json TEXT NOT NULL,
  accepted INTEGER NOT NULL CHECK(accepted IN (0,1)),
  reasons TEXT
);

CREATE TABLE IF NOT EXISTS recon_aliases (
  id INTEGER PRIMARY KEY,
  rut TEXT,
  razon_social TEXT,
  pattern TEXT,
  confidence REAL DEFAULT 0.5,
  hits INTEGER DEFAULT 0
);

-- Índices recomendados
CREATE INDEX IF NOT EXISTS idx_links_bank     ON recon_links(bank_movement_id);
CREATE INDEX IF NOT EXISTS idx_links_sales    ON recon_links(sales_invoice_id);
CREATE INDEX IF NOT EXISTS idx_links_purchase ON recon_links(purchase_invoice_id);

-- Normalización de cartola
ALTER TABLE bank_movements ADD COLUMN descripcion_norm TEXT; -- si no existe
UPDATE bank_movements SET descripcion_norm = UPPER(REPLACE(REPLACE(descripcion, '  ',' '), '\t',' '));
CREATE INDEX IF NOT EXISTS idx_bm_date   ON bank_movements(fecha);
CREATE INDEX IF NOT EXISTS idx_bm_amount ON bank_movements(monto);
CREATE INDEX IF NOT EXISTS idx_bm_norm   ON bank_movements(descripcion_norm);
```

### 1.2 Postgres (DDL equivalente)
```sql
-- migrations/20250914_recon_tables_pg.sql
CREATE TABLE IF NOT EXISTS recon_reconciliations (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  context TEXT NOT NULL CHECK(context IN ('bank','sales','purchase','expense','payroll','tax')),
  confidence NUMERIC(5,4),
  user_id TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS recon_links (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  reconciliation_id BIGINT NOT NULL REFERENCES recon_reconciliations(id) ON DELETE CASCADE,
  bank_movement_id BIGINT,
  sales_invoice_id BIGINT,
  purchase_invoice_id BIGINT,
  expense_id BIGINT,
  payroll_id BIGINT,
  tax_id BIGINT,
  amount NUMERIC(18,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS recon_training_events (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  context TEXT,
  source_json JSONB NOT NULL,
  chosen_json JSONB NOT NULL,
  accepted BOOLEAN NOT NULL,
  reasons TEXT
);

CREATE TABLE IF NOT EXISTS recon_aliases (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  rut TEXT,
  razon_social TEXT,
  pattern TEXT,
  confidence NUMERIC(5,4) DEFAULT 0.5,
  hits BIGINT DEFAULT 0
);

-- Normalización de cartola
ALTER TABLE bank_movements ADD COLUMN IF NOT EXISTS descripcion_norm TEXT;
UPDATE bank_movements SET descripcion_norm = UPPER(regexp_replace(descripcion, '\\s+', ' ', 'g')) WHERE descripcion_norm IS NULL;
CREATE INDEX IF NOT EXISTS idx_bm_date   ON bank_movements(fecha);
CREATE INDEX IF NOT EXISTS idx_bm_amount ON bank_movements(monto);
CREATE INDEX IF NOT EXISTS idx_bm_norm   ON bank_movements(descripcion_norm);
```

---

## 2) Backend (Flask) — Endpoints y Adapter

### 2.1 Adapter al motor inteligente
```py
# backend/reconcile_adapter.py
from typing import List, Dict, Any, Optional

# Reemplaza import si tu módulo vive en otro path
try:
    from services.conciliacion_bancaria.core.intelligent_matching import suggest as smart_suggest
except Exception:
    # Fallback simple si el servicio no está disponible
    def smart_suggest(source: Dict[str, Any], options: Dict[str, Any]) -> List[Dict[str, Any]]:
        cand = []
        return cand

DEFAULTS = {
    'amount_tol': 0.01,  # 1%
    'days': 5,
}

def build_source(context: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza la solicitud desde UI para el motor"""
    src = {
        'context': context,              # 'bank'|'sales'|'purchase'|'expense'|'payroll'|'tax'
        'id': payload.get('id'),
        'amount': payload.get('amount'),
        'date': payload.get('date'),
        'currency': payload.get('currency', 'CLP'),
        'ref': payload.get('ref'),
    }
    return src

def suggest(context: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    src = build_source(context, payload)
    opts = {
        'amount_tol': payload.get('amount_tol', DEFAULTS['amount_tol']),
        'days':       payload.get('days', DEFAULTS['days']),
    }
    items = smart_suggest(src, opts) or []
    # Asegurar forma {candidate, confidence, reasons}
    norm = []
    for it in items:
        norm.append({
            'candidate': it.get('candidate', {}),
            'confidence': float(it.get('confidence', 0.0)),
            'reasons': it.get('reasons', []),
        })
    # ordenar por mayor confianza
    norm.sort(key=lambda x: x['confidence'], reverse=True)
    return norm[:10]
```

### 2.2 Rutas `/sugerencias`, `/preview`, `/confirmar`
```py
# backend/conciliacion_api.py
from flask import Blueprint, request, jsonify
import sqlite3
from datetime import datetime
from typing import Any, Dict
from reconcile_adapter import suggest

bp = Blueprint('recon', __name__)
DB_PATH = 'data/chipax_data.db'  # ajustar

class Unprocessable(ValueError):
    def __init__(self, error, detail=None, **extra):
        self.payload = {'error': error, 'detail': detail}
        self.payload.update(extra)

@bp.errorhandler(Unprocessable)
def _unprocessable(e):
    return jsonify(e.payload), 422


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

@bp.post('/api/conciliacion/sugerencias')
def api_sugerencias():
    body = request.get_json(force=True)
    context = body.get('source_type')
    if context not in {'bank','sales','purchase','expense','payroll','tax'}:
        raise Unprocessable('invalid_context', 'source_type inválido')
    items = suggest(context, body)
    return jsonify({'items': items})

@bp.post('/api/conciliacion/preview')
def api_preview():
    body = request.get_json(force=True)
    links = body.get('links') or []
    if not links:
        raise Unprocessable('invalid_payload', 'links vacío')
    # Simular: sumar montos por invoice, marcar movimientos
    by_invoice: Dict[Any, float] = {}
    by_movement: Dict[Any, float] = {}
    for l in links:
        amt = float(l.get('amount', 0))
        if l.get('sales_invoice_id'):
            by_invoice[('sales', l['sales_invoice_id'])] = by_invoice.get(('sales', l['sales_invoice_id']), 0)+amt
        if l.get('purchase_invoice_id'):
            by_invoice[('purchase', l['purchase_invoice_id'])] = by_invoice.get(('purchase', l['purchase_invoice_id']), 0)+amt
        if l.get('bank_movement_id'):
            by_movement[l['bank_movement_id']] = by_movement.get(l['bank_movement_id'], 0)+amt
    return jsonify({'ok': True, 'preview': {'invoice_deltas': by_invoice, 'movement_deltas': by_movement}})

@bp.post('/api/conciliacion/confirmar')
def api_confirmar():
    body = request.get_json(force=True)
    context = body.get('context')
    links = body.get('links') or []
    meta = body.get('metadata') or {}
    confidence = body.get('confidence')
    reasons = body.get('reasons') or []
    if not links:
        raise Unprocessable('invalid_payload', 'links vacío')
    con = db(); cur = con.cursor()
    cur.execute("INSERT INTO recon_reconciliations(context, confidence, user_id, notes) VALUES(?,?,?,?)",
                (context, confidence, meta.get('user_id'), meta.get('notes')))
    rid = cur.lastrowid
    for l in links:
        cur.execute("""
            INSERT INTO recon_links(reconciliation_id, bank_movement_id, sales_invoice_id, purchase_invoice_id, expense_id, payroll_id, tax_id, amount)
            VALUES(?,?,?,?,?,?,?,?)
        """, (rid, l.get('bank_movement_id'), l.get('sales_invoice_id'), l.get('purchase_invoice_id'), l.get('expense_id'), l.get('payroll_id'), l.get('tax_id'), l.get('amount')))
    con.commit()
    return jsonify({'ok': True, 'reconciliation_id': rid})
```

**Registrar blueprint en el server**
```py
# backend/server.py
from conciliacion_api import bp as recon_bp
app.register_blueprint(recon_bp)
```

---

## 3) Cliente TS (frontend/lib)
```ts
// frontend/lib/reconApi.ts
const API = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:5555';

export async function getSuggestions(payload: any){
  const r = await fetch(`${API}/api/conciliacion/sugerencias`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  const j = await r.json(); if(!r.ok) throw new Error(j.detail||j.error||'sugerencias failed'); return j;
}

export async function previewRecon(payload: any){
  const r = await fetch(`${API}/api/conciliacion/preview`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  const j = await r.json(); if(!r.ok) throw new Error(j.detail||j.error||'preview failed'); return j;
}

export async function confirmRecon(payload: any){
  const r = await fetch(`${API}/api/conciliacion/confirmar`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  const j = await r.json(); if(!r.ok) throw new Error(j.detail||j.error||'confirm failed'); return j;
}
```

---

## 4) UI — Drawer y botones

### 4.1 `ConciliarButton.tsx`
```tsx
'use client';
import React from 'react';

export default function ConciliarButton({ onClick }:{ onClick:()=>void }){
  return (
    <button onClick={onClick} className="border px-3 py-1 rounded-full text-sm">
      Conciliar
    </button>
  );
}
```

### 4.2 `ReasonChips.tsx`
```tsx
'use client';
import React from 'react';
export default function ReasonChips({ reasons }:{ reasons:string[] }){
  return (
    <div className="flex flex-wrap gap-1">
      {reasons?.map((r,i)=> <span key={i} className="px-2 py-0.5 text-xs rounded-full border">{r}</span>)}
    </div>
  );
}
```

### 4.3 `ReconcileDrawer.tsx`
```tsx
'use client';
import React, { useEffect, useState } from 'react';
import { getSuggestions, previewRecon, confirmRecon } from '@/lib/reconApi';
import ReasonChips from './ReasonChips';

export default function ReconcileDrawer({ context, source }:{ context:'bank'|'sales'|'purchase'|'expense'|'payroll'|'tax'; source:any }){
  const [open, setOpen] = useState(true);
  const [items, setItems] = useState<any[]>([]);
  const [selected, setSelected] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(()=>{ (async()=>{
    setLoading(true);
    try{
      const j = await getSuggestions({ source_type: context, ...source });
      setItems(j.items||[]);
    } finally { setLoading(false); }
  })(); },[context, JSON.stringify(source)]);

  async function onPreview(){
    const links = selected.map((c:any)=> ({
      bank_movement_id: context==='bank'? source.id : c.candidate.bank_movement_id,
      sales_invoice_id: context==='sales'? source.id : c.candidate.sales_invoice_id,
      purchase_invoice_id: context==='purchase'? source.id : c.candidate.purchase_invoice_id,
      amount: c.candidate.amount || source.amount
    }));
    const j = await previewRecon({ context, links });
    alert('Preview OK');
  }

  async function onConfirm(){
    const links = selected.map((c:any)=> ({
      bank_movement_id: context==='bank'? source.id : c.candidate.bank_movement_id,
      sales_invoice_id: context==='sales'? source.id : c.candidate.sales_invoice_id,
      purchase_invoice_id: context==='purchase'? source.id : c.candidate.purchase_invoice_id,
      amount: c.candidate.amount || source.amount
    }));
    const j = await confirmRecon({ context, links, metadata:{ user_id:'me' }, confidence: selected[0]?.confidence, reasons: selected[0]?.reasons });
    alert(`Conciliado #${j.reconciliation_id}`);
    setOpen(false);
  }

  if(!open) return null;
  return (
    <div className="fixed inset-y-0 right-0 w-[420px] bg-white border-l p-4 z-40 overflow-auto">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Conciliar</h2>
        <button className="text-sm" onClick={()=>setOpen(false)}>Cerrar</button>
      </div>
      {loading && <div className="text-sm text-neutral-500">Buscando sugerencias…</div>}
      <div className="space-y-2">
        {items.map((it:any, idx:number)=> (
          <div key={idx} className={`rounded-2xl border p-3 ${selected.includes(it)?'ring-1':''}`}>
            <div className="flex items-center justify-between">
              <div className="text-sm">
                <div className="font-medium">{it.candidate?.doc || it.candidate?.type} • {Number(it.candidate?.amount||0).toLocaleString()}</div>
                <div className="text-neutral-500">{it.candidate?.fecha}</div>
              </div>
              <div className="text-xs">conf: {(it.confidence*100).toFixed(1)}%</div>
            </div>
            <div className="mt-2"><ReasonChips reasons={it.reasons||[]} /></div>
            <div className="mt-2 flex gap-2">
              <button className="border px-2 py-1 rounded" onClick={()=>setSelected([it])}>Elegir</button>
              <button className="border px-2 py-1 rounded" onClick={()=>setSelected([...selected, it])}>Agregar (Split)</button>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex gap-2">
        <button className="border px-3 py-1 rounded" onClick={onPreview}>Preview</button>
        <button className="border px-3 py-1 rounded" onClick={onConfirm}>Confirmar</button>
      </div>
    </div>
  );
}
```

---

## 5) cURL de prueba rápida
```bash
# Sugerencias para una factura de venta
curl -s X POST http://localhost:5555/api/conciliacion/sugerencias \
  -H 'Content-Type: application/json' \
  -d '{"source_type":"sales","id":8812,"amount":25369786,"date":"2025-09-10","currency":"CLP"}' | jq

# Preview de conciliación banco↔venta
curl -s X POST http://localhost:5555/api/conciliacion/preview \
  -H 'Content-Type: application/json' \
  -d '{"context":"bank","links":[{"bank_movement_id":1001,"sales_invoice_id":8812,"amount":25369786}]}' | jq

# Confirmar
curl -s X POST http://localhost:5555/api/conciliacion/confirmar \
  -H 'Content-Type: application/json' \
  -d '{"context":"bank","links":[{"bank_movement_id":1001,"sales_invoice_id":8812,"amount":25369786}],"confidence":0.94,"reasons":["monto=exact","fecha=+1d"]}' | jq
```

---

## 6) Notas finales
- Este código es **boilerplate**: reemplaza nombres de tablas/vistas si tu canónico difiere.
- Integra el *adapter* con tu motor en `services/conciliacion_bancaria/core/intelligent_matching.py`.
- Una vez validado, conecta el **drawer** a las pantallas de **Factura Venta/Compra** y **Cartola** con el botón **Conciliar**.
- Opcional (futuro cercano): endpoint `POST /api/conciliacion/rules` para crear reglas automáticas a partir de una conciliación confirmada.

