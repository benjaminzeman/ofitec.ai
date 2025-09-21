# OFITEC — Plan técnico: **GRN (Recepciones)** + **Subcontratos (Avances/Retenciones)** + **Portal de Pagos a Proveedores**
**Propósito:** Implementar tres capacidades clave, coherentes con *docs_oficiales* (Ley de Puertos 3001/5555, Ley de Base de Datos, Vistas Canónicas, Estrategia Visual) y el módulo **Proyecto 360°**:
- **(4)** Recepciones (**GRN**) y **3‑way match** real (OC → Recepción → Factura).  
- **(5)** Subcontratos con **certificados de avance**, **anticipos** y **retenciones**.  
- **(6)** Portal de **visibilidad de pagos** para proveedores ("¿Cuándo cobro?").

> Nota: **Rendiciones/petty cash** se excluye a propósito (se sugiere integrar con Rindegastos en el futuro).

---

## 0) Principios y lineamientos
- **DB Canónica**: La API de producción sólo lee/escribe en **tablas/vistas canónicas**. Nada crudo.  
- **Proyecto‑centrismo**: toda operación referencia `project_id|project_name` normalizados (y `project_aliases` si aplica).  
- **Reglas duras** (server‑side):  
  **Factura ≤ OC** y **Factura ≤ Recepción** (por línea y total), **Pago ≤ Factura**.  
- **Auditoría**: bitácora de cambios (usuario, timestamp, motivo), y versionado en cambios sustantivos (orden de cambio/ajustes).  
- **Experiencia**: flujos simples, semáforos, y explicabilidad (UI muestra las razones y acciones sugeridas).

---

# (4) Recepciones (GRN) + 3‑way match real

## 4.1 Modelo de datos (SQLite flavor; anotar diferencias Postgres)
```sql
-- Header de recepción
CREATE TABLE IF NOT EXISTS goods_receipts (
  grn_id            INTEGER PRIMARY KEY,
  project_id        INTEGER NOT NULL,
  po_id             TEXT NOT NULL,
  vendor_id         INTEGER,
  received_at       TEXT NOT NULL,      -- ISO date/time
  received_by       TEXT,               -- usuario
  location          TEXT,               -- bodega/obra
  notes             TEXT,
  status            TEXT CHECK (status IN ('draft','posted','reversed')) DEFAULT 'posted'
);

-- Líneas de recepción (parciales/varias por línea de OC)
CREATE TABLE IF NOT EXISTS goods_receipt_lines (
  id                INTEGER PRIMARY KEY,
  grn_id            INTEGER NOT NULL,
  po_line_id        TEXT NOT NULL,
  qty_received      REAL NOT NULL,
  uom               TEXT,
  unit_price_copy   REAL,               -- precio de referencia al recibir (para difs)
  batch_serial      TEXT,               -- opcional
  remark            TEXT
);
CREATE INDEX IF NOT EXISTS idx_grn_line_grn ON goods_receipt_lines(grn_id);
CREATE INDEX IF NOT EXISTS idx_grn_line_poline ON goods_receipt_lines(po_line_id);

-- Devoluciones/ajustes negativos (RMA/NCR)
CREATE TABLE IF NOT EXISTS goods_return_lines (
  id                INTEGER PRIMARY KEY,
  ref_grn_line_id   INTEGER NOT NULL,   -- contra qué recepción
  qty_returned      REAL NOT NULL,
  reason            TEXT,
  created_at        TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Vistas canónicas de soporte**
```sql
-- Acumulado recibido por línea de OC
DROP VIEW IF EXISTS v_po_line_received_accum;
CREATE VIEW v_po_line_received_accum AS
SELECT
  l.po_line_id,
  SUM(COALESCE(l.qty_received,0))
    - COALESCE((SELECT SUM(r.qty_returned) FROM goods_return_lines r WHERE r.ref_grn_line_id = l.id),0)
    AS qty_received_accum
FROM goods_receipt_lines l
GROUP BY l.po_line_id;

-- Estado 3-way por línea de OC (qty y monto)
DROP VIEW IF EXISTS v_3way_status_po_line;
CREATE VIEW v_3way_status_po_line AS
SELECT
  pol.po_line_id,
  pol.po_id,
  pol.qty AS po_qty,
  pol.unit_price AS po_unit_price,
  COALESCE(rec.qty_received_accum,0) AS recv_qty,
  COALESCE(inv.qty_invoiced,0) AS inv_qty,
  CASE
    WHEN COALESCE(inv.qty_invoiced,0) <= COALESCE(rec.qty_received_accum,0)
     AND COALESCE(rec.qty_received_accum,0) <= pol.qty THEN 'matching'
    WHEN COALESCE(inv.qty_invoiced,0) > COALESCE(rec.qty_received_accum,0) THEN 'invoice_over_receipt'
    WHEN COALESCE(rec.qty_received_accum,0) > pol.qty THEN 'over_received'
    ELSE 'under_received'
  END AS match_status
FROM purchase_order_lines pol
LEFT JOIN v_po_line_received_accum rec ON rec.po_line_id = pol.po_line_id
LEFT JOIN (
  SELECT invoice_lines.po_line_id, SUM(invoice_lines.qty) AS qty_invoiced
  FROM invoice_lines -- vista/tabla canónica de AP lines
  GROUP BY invoice_lines.po_line_id
) inv ON inv.po_line_id = pol.po_line_id;
```
> **Postgres**: usar `DATE/TIMESTAMP`, FK explícitas y `generated always as identity`.

## 4.2 Validaciones de negocio
- **Al crear factura AP**: por cada `po_line_id`, `qty_facturada_acum ≤ qty_recibida_acum` y `Monto_facturado ≤ PO_line_total`.  
- **Al registrar recepción**: no permitir `recv_qty_acum > po_qty` salvo **ajuste aprobado** (orden de cambio + bitácora).  
- **Devolución**: genera `goods_return_lines` (negativo) y bloquea pago de esa porción si ya facturada (flujo de **nota de crédito**).

## 4.3 API (5555) endpoints
- `GET /api/projects/:id/grn` → lista de GRN con totales y discrepancias.  
- `POST /api/grn` → crear GRN (header + líneas).  
- `POST /api/grn/:grn_id/return` → crear devolución/ajuste.  
- `GET /api/threeway/po/:po_id` → estado 3‑way por líneas (para UI y auditoría).  
- **Errores 422**: `over_received`, `invoice_over_receipt`.

## 4.4 UI/UX
- **Recepción rápida**: buscar OC → ver líneas → ingresar cantidades (autofocus), adjuntar guía (Drive), guardar.  
- **Semáforos** por línea: verde (*matching*), ámbar (*under*), rojo (*over* / *invoice_over_receipt*).  
- **Scanner opcional**: lector de código/QR para acelerar selección de líneas.

---

# (5) Subcontratos: Avances (certificados), Anticipos y Retenciones

## 5.1 Modelo (extensión de contratos ya definida)
```sql
-- Anticipos entregados al contratista (se amortizan en certificados)
CREATE TABLE IF NOT EXISTS contract_advances (
  id INTEGER PRIMARY KEY,
  contract_id INTEGER NOT NULL,
  advance_date TEXT,
  amount REAL NOT NULL,
  retained_pct REAL DEFAULT 0,   -- si el anticipo tiene retención
  notes TEXT
);

-- Ledger de retenciones (acumuladas y liberadas)
CREATE TABLE IF NOT EXISTS contract_retentions (
  id INTEGER PRIMARY KEY,
  contract_id INTEGER NOT NULL,
  source TEXT CHECK (source IN ('certificate','penalty','other')),
  source_id INTEGER,
  amount REAL NOT NULL,
  retained_at TEXT,
  released_at TEXT,
  release_reason TEXT
);

-- Certificados de avance (ya propuestos)
-- progress_certificates & progress_certificate_lines (ver playbook anterior)
```

**Reglas**
- **Certificado** calcula: `bruto_periodo` (medición * PU), `retención_periodo` (= % contrato o certificado), `amortización_anticipo` (según política), `neto_pagable`.  
- `Factura AP` se **genera desde certificado** (evita inconsistencias).  
- Retenciones se registran en `contract_retentions` y alimentan **cashflow** (salida diferida al liberar).  

**Vistas**
```sql
DROP VIEW IF EXISTS v_contract_status;
CREATE VIEW v_contract_status AS
SELECT c.id AS contract_id,
       c.project_id,
       COALESCE(scope_total.total_scope,0) AS contratado,
       COALESCE(cert.total_certified,0) AS certificado,
       COALESCE(pay.total_paid,0) AS pagado,
       COALESCE(ret.total_retained,0) AS retenido,
       (COALESCE(cert.total_certified,0) - COALESCE(pay.total_paid,0) - COALESCE(ret.total_retained,0)) AS saldo_por_pagar
FROM contracts c
LEFT JOIN (
  SELECT contract_id, SUM(qty * unit_price) AS total_scope
  FROM contract_scope GROUP BY contract_id
) scope_total USING(contract_id)
LEFT JOIN (
  SELECT pc.contract_id, SUM(l.amount) AS total_certified
  FROM progress_certificates pc
  JOIN progress_certificate_lines l ON l.certificate_id = pc.id
  GROUP BY pc.contract_id
) cert ON cert.contract_id = c.id
LEFT JOIN (
  SELECT a.contract_id, SUM(p.paid_amount) AS total_paid
  FROM ap_payments p -- vista pagos AP por contrato (derivable via invoice→contract)
  JOIN ap_invoices a ON a.id = p.invoice_id
  GROUP BY a.contract_id
) pay ON pay.contract_id = c.id
LEFT JOIN (
  SELECT contract_id, SUM(amount) AS total_retained
  FROM contract_retentions WHERE released_at IS NULL
  GROUP BY contract_id
) ret ON ret.contract_id = c.id;
```

## 5.2 API (5555)
- `POST /api/contracts/:id/advance` → registrar anticipo.  
- `POST /api/contracts/:id/certificate` → crear certificado (líneas y cálculo neto).  
- `POST /api/certificates/:id/generate-invoice` → crear factura AP desde certificado (incluye retención/amortización).  
- `POST /api/contracts/:id/retention/release` → liberar retención (flujo de aprobación).  
- `GET /api/contracts/:id/status` → KPIs del contrato (contratado, certificado, pagado, retenido, saldos).

## 5.3 UI/UX
- **Tab Subcontratos** en Proyecto: tarjetas por contrato con barras (Contratado/Certificado/Pagado/Retenido) y tabla de certificados.  
- **Wizard Certificado**: seleccionar período → medir por **contract_scope** → calcular neto (retención/anticipo) → generar factura AP.  
- **Ledger Retenciones**: listado con filtros y botón **Liberar** (maker‑checker).

---

# (6) Portal de Pagos a Proveedores (visibilidad "¿cuándo cobro?")

## 6.1 Modelo y seguridad
```sql
CREATE TABLE IF NOT EXISTS supplier_portal_tokens (
  id INTEGER PRIMARY KEY,
  vendor_id INTEGER NOT NULL,
  token TEXT UNIQUE NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  expires_at TEXT,
  revoked_at TEXT
);
```
- El **token** se ata a `vendor_id`. Las consultas se filtran por proveedor; sin login complejo.  
- Expiración y revocación soportadas.

**Vistas** (pipeline del proveedor)
```sql
DROP VIEW IF EXISTS v_vendor_pipeline;
CREATE VIEW v_vendor_pipeline AS
SELECT v.id AS vendor_id,
       po.po_id,
       po.zoho_project_name AS project_name,
       po.status AS po_status,
       COALESCE(rec.recv_qty,0) AS qty_received,
       inv.invoice_id,
       inv.invoice_date,
       inv.amount_total,
       inv.due_date,
       pay.paid_amount,
       pay.paid_date
FROM vendors_unified v
LEFT JOIN purchase_orders_unified po ON po.vendor_id = v.id
LEFT JOIN (
  SELECT pol.po_id, SUM(r.qty_received) AS recv_qty
  FROM goods_receipt_lines r
  JOIN purchase_order_lines pol ON pol.po_line_id = r.po_line_id
  GROUP BY pol.po_id
) rec ON rec.po_id = po.po_id
LEFT JOIN v_ap_invoices inv ON inv.po_id = po.po_id       -- vista canónica AP
LEFT JOIN v_ap_payments pay ON pay.invoice_id = inv.invoice_id; -- pagos AP
```

## 6.2 API (5555)
- `GET /api/supplier-portal/:token/summary` → KPIs del proveedor (OC abiertas, facturas emitidas, programaciones, pagos).  
- `GET /api/supplier-portal/:token/invoices` → listado con estado y **fecha estimada de pago** (due_date o programación).  
- `POST /api/supplier-portal/:token/ack` → proveedor acusa recibo de OC o confirma recepción (opcional).  
- **WhatsApp**: enlace corto con el token para acceso directo desde mensajes.

## 6.3 UI/UX
- **Vista pública** (3001) por token:  
  - Tarjetas: OC abiertas, facturas por cobrar, pagos recientes.  
  - Tabla de **facturas**: monto, estado, due_date/fecha programada, proyecto, botón “ver detalle”.  
  - Acciones: **Confirmar** recepción, **Subir** factura PDF (si se habilita), **Enviar** consulta (WhatsApp).  
- **Diseño** minimal (Inter, bordes 1px, radius 12, sin sombras), accesible móvil.

---

## 7) Integración con Proyecto 360° y Cashflow
- **Proyecto 360°**:  
  - Compras/OC muestran **Recepciones** (GRN) por línea y estado 3‑way.  
  - Subcontratos: KPIs del **v_contract_status** y lista de certificados/retenciones.  
  - Finanzas: **outflows expected** se nutren de:  
    (a) materiales via `delivery_plan→invoice→payment_terms`,  
    (b) subcontratos via **certificados** (neto pagable),  
    (c) retenciones **liberables** → bucket futuro.  
- **Cashflow**:  
  - `v_cashflow_expected` incluye certificados (servicios) y recepciones programadas (materiales).  
  - `v_cashflow_actual` desde cartola (pagos conciliados).  
  - Variancia por mes y explicación (IA) en Proyecto.

---

## 8) Validaciones críticas (server‑side)
- **GRN**: `recv_qty_acum ≤ po_qty`, salvo **orden de cambio**.  
- **Factura AP**: `qty_facturada ≤ qty_recibida` **y** `monto_facturado ≤ monto_OC`, por línea y por OC.  
- **Pagos AP**: `pago_acum ≤ factura_total`.  
- **Subcontratos**: `certificado ≤ contract_scope`, neto = bruto − retención − amortización anticipo.  
- **Portal**: token válido/no expirado; limitar acciones al `vendor_id` asociado.

---

## 9) Plan de implementación (2 sprints)
**Sprint A (2–3 semanas)**  
1) Tablas GRN + vistas `v_po_line_received_accum`, `v_3way_status_po_line`.  
2) Endpoints GRN y validaciones 3‑way; UI recepción básica + semáforos.  
3) Extender `v_cashflow_expected` con certificados y GRN.  

**Sprint B (3–4 semanas)**  
4) Subcontratos: `contract_advances`, `contract_retentions`; endpoints certificado→factura; ledger retenciones.  
5) Portal proveedor: tokens, endpoints summary/invoices, vista pública móvil.  
6) Auditoría y maker‑checker para liberación de retenciones y ajustes GRN.

---

## 10) Notas para Copilot
- Respetar Ley de Puertos y DB Canónica; si una vista no existe, **crear la vista**.  
- Todas las reglas críticas → **422** con `{error, detail, ...}` y logs.  
- Mantener normalización de `project_name` y uso de `project_aliases` para joins.  
- En UI, usar tokens visuales estándar (Inter, lime #84CC16, radio 12, sin sombras) y componentes reutilizables (KPICard, Table, Badges).


---

## 11) SQL — **Variantes Postgres** (DDL + Vistas)
> Usar `GENERATED ALWAYS AS IDENTITY`, `TIMESTAMPTZ/DATE`, `NUMERIC(18,2)` para montos, `FK` explícitas y `ON UPDATE/DELETE` conservadoras. Ajustar nombres de tablas según tu canónico. Todos los objetos en **esquema** `public` salvo que definas otro.

```sql
-- (4) GRN / Recepciones
CREATE TABLE IF NOT EXISTS goods_receipts (
  grn_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id    BIGINT NOT NULL,
  po_id         TEXT   NOT NULL,
  vendor_id     BIGINT,
  received_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  received_by   TEXT,
  location      TEXT,
  notes         TEXT,
  status        TEXT NOT NULL CHECK (status IN ('draft','posted','reversed')) DEFAULT 'posted'
);

CREATE TABLE IF NOT EXISTS goods_receipt_lines (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  grn_id        BIGINT NOT NULL REFERENCES goods_receipts(grn_id) ON DELETE CASCADE,
  po_line_id    TEXT   NOT NULL,
  qty_received  NUMERIC(18,4) NOT NULL,
  uom           TEXT,
  unit_price_copy NUMERIC(18,4),
  batch_serial  TEXT,
  remark        TEXT
);
CREATE INDEX IF NOT EXISTS idx_grn_line_grn     ON goods_receipt_lines(grn_id);
CREATE INDEX IF NOT EXISTS idx_grn_line_poline  ON goods_receipt_lines(po_line_id);

CREATE TABLE IF NOT EXISTS goods_return_lines (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ref_grn_line_id BIGINT NOT NULL REFERENCES goods_receipt_lines(id) ON DELETE RESTRICT,
  qty_returned    NUMERIC(18,4) NOT NULL,
  reason          TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- (5) Subcontratos: anticipos y retenciones
CREATE TABLE IF NOT EXISTS contract_advances (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  contract_id   BIGINT NOT NULL REFERENCES contracts(id) ON DELETE RESTRICT,
  advance_date  DATE,
  amount        NUMERIC(18,2) NOT NULL,
  retained_pct  NUMERIC(9,4) DEFAULT 0,
  notes         TEXT
);

CREATE TABLE IF NOT EXISTS contract_retentions (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  contract_id   BIGINT NOT NULL REFERENCES contracts(id) ON DELETE RESTRICT,
  source        TEXT NOT NULL CHECK (source IN ('certificate','penalty','other')),
  source_id     BIGINT,
  amount        NUMERIC(18,2) NOT NULL,
  retained_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  released_at   TIMESTAMPTZ,
  release_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_ret_contract ON contract_retentions(contract_id);
CREATE INDEX IF NOT EXISTS idx_ret_open     ON contract_retentions(contract_id) WHERE released_at IS NULL;

-- (6) Portal de pagos proveedor (token)
CREATE TABLE IF NOT EXISTS supplier_portal_tokens (
  id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  vendor_id  BIGINT NOT NULL REFERENCES vendors_unified(id) ON DELETE CASCADE,
  token      TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ
);

-- Vistas equivalentes (Postgres flavor)
DROP VIEW IF EXISTS v_po_line_received_accum;
CREATE VIEW v_po_line_received_accum AS
SELECT
  l.po_line_id,
  COALESCE(SUM(l.qty_received),0) - COALESCE( (
    SELECT SUM(r.qty_returned) FROM goods_return_lines r WHERE r.ref_grn_line_id = l.id
  ),0) AS qty_received_accum
FROM goods_receipt_lines l
GROUP BY l.po_line_id;

DROP VIEW IF EXISTS v_3way_status_po_line;
CREATE VIEW v_3way_status_po_line AS
WITH inv AS (
  SELECT il.po_line_id, SUM(il.qty) AS qty_invoiced
  FROM invoice_lines il
  GROUP BY il.po_line_id
)
SELECT
  pol.po_line_id,
  pol.po_id,
  pol.qty                     AS po_qty,
  pol.unit_price              AS po_unit_price,
  COALESCE(rec.qty_received_accum,0) AS recv_qty,
  COALESCE(inv.qty_invoiced,0)       AS inv_qty,
  CASE
    WHEN COALESCE(inv.qty_invoiced,0) <= COALESCE(rec.qty_received_accum,0)
     AND COALESCE(rec.qty_received_accum,0) <= pol.qty THEN 'matching'
    WHEN COALESCE(inv.qty_invoiced,0) > COALESCE(rec.qty_received_accum,0) THEN 'invoice_over_receipt'
    WHEN COALESCE(rec.qty_received_accum,0) > pol.qty THEN 'over_received'
    ELSE 'under_received'
  END AS match_status
FROM purchase_order_lines pol
LEFT JOIN v_po_line_received_accum rec ON rec.po_line_id = pol.po_line_id
LEFT JOIN inv ON inv.po_line_id = pol.po_line_id;

-- Buckets mensuales en Postgres
DROP VIEW IF EXISTS v_cashflow_expected_project_pg;
CREATE VIEW v_cashflow_expected_project_pg AS
SELECT
  o.zoho_project_name AS project_name,
  date_trunc('month', p.est_payment_date)::date AS bucket_month,
  SUM(p.amount)::numeric(18,2) AS expected_outflow
FROM v_po_line_payment_schedule p
JOIN purchase_orders_unified o ON o.po_id = p.po_id
GROUP BY o.zoho_project_name, date_trunc('month', p.est_payment_date)::date;
```

---

## 12) **API** — Ejemplos de *payloads* (request/response)

### 12.1 GRN (Recepciones)
**POST** `/api/grn`
```json
{
  "project_id": 42,
  "po_id": "PO-2025-00123",
  "vendor_id": 17,
  "received_at": "2025-09-14T10:35:00-04:00",
  "location": "Bodega Obra Norte",
  "lines": [
    { "po_line_id": "POL-0001", "qty_received": 600, "uom": "kg" },
    { "po_line_id": "POL-0002", "qty_received": 12,  "uom": "und" }
  ]
}
```
**200**
```json
{ "ok": true, "grn_id": 981, "posted": true }
```
**422** `over_received`
```json
{ "error": "over_received", "detail": "qty exceeds PO", "po_line_id": "POL-0001", "po_qty": 1000, "recv_accum": 1000, "attempt": 50 }
```

**GET** `/api/threeway/po/PO-2025-00123`
```json
{
  "po_id": "PO-2025-00123",
  "lines": [
    { "po_line_id": "POL-0001", "po_qty": 1000, "recv_qty": 1000, "inv_qty": 850, "status": "under_received" },
    { "po_line_id": "POL-0002", "po_qty": 12,   "recv_qty": 12,   "inv_qty": 12,  "status": "matching" }
  ]
}
```

**POST** `/api/grn/981/return`
```json
{ "ref_grn_line_id": 3341, "qty_returned": 50, "reason": "Daño en transporte" }
```
**200** `{ "ok": true, "return_id": 777 }`

---

### 12.2 Subcontratos (Certificados, Anticipos y Retenciones)
**POST** `/api/contracts/55/advance`
```json
{ "advance_date": "2025-09-10", "amount": 15000000, "retained_pct": 0.05, "notes": "Anticipo inicio obra" }
```

**POST** `/api/contracts/55/certificate`
```json
{
  "period_start": "2025-09-01",
  "period_end":   "2025-09-30",
  "retention_pct": 0.05,
  "lines": [
    { "contract_scope_id": 901, "qty_measured": 120, "amount": 4800000 },
    { "contract_scope_id": 902, "qty_measured": 60,  "amount": 2100000 }
  ],
  "amortize_advances": true
}
```
**200** (cálculo del neto pagable)
```json
{
  "certificate_id": 311,
  "gross": 6900000,
  "retention": 345000,
  "advance_amortization": 1200000,
  "net_payable": 5355000
}
```

**POST** `/api/certificates/311/generate-invoice`
```json
{ "invoice_date": "2025-10-05" }
```
**200** `{ "invoice_id": 8801, "amount_total": 6372450, "due_date": "2025-11-04" }`

**POST** `/api/contracts/55/retention/release`
```json
{ "retention_id": 122, "release_date": "2026-02-15", "reason": "Recepción final + Acta conforme" }
```
**200** `{ "ok": true }`

**GET** `/api/contracts/55/status`
```json
{
  "contract_id": 55,
  "project_id": 42,
  "contratado": 31000000,
  "certificado": 14500000,
  "pagado": 9800000,
  "retenido": 870000,
  "saldo_por_pagar": 3820000
}
```

---

### 12.3 Portal de Pagos (Proveedor)
**GET** `/api/supplier-portal/{token}/summary`
```json
{
  "vendor_id": 17,
  "open_pos": 6,
  "invoices_issued": 14,
  "to_be_paid": 4,
  "last_payment": { "amount": 2450000, "date": "2025-09-12" }
}
```
**GET** `/api/supplier-portal/{token}/invoices`
```json
{
  "items": [
    { "invoice_id": 9001, "po_id": "PO-2025-00123", "project": "Edificio Centro", "amount_total": 2745600, "status": "issued", "due_date": "2025-10-10" },
    { "invoice_id": 8991, "po_id": "PO-2025-00088", "project": "Planta Sur", "amount_total": 1120000, "status": "paid",   "paid_date": "2025-09-05" }
  ]
}
```

---

## 13) **Frontend React** — Componentes base (Next.js + Tailwind + Recharts)
> Estilo minimal: Inter, bordes 1px, `rounded-2xl`, sin sombras. Componentes *client* cuando corresponda. Reutilizar en **Proyecto 360°**.

### 13.1 `GRNReceiveForm.tsx`
```tsx
'use client';
import React, { useEffect, useState } from 'react';

export default function GRNReceiveForm({ poId }:{ poId:string }){
  const [lines, setLines] = useState<{po_line_id:string; desc?:string; po_qty:number; recv_qty?:number}[]>([]);
  const [qty, setQty] = useState<Record<string, number>>({});

  useEffect(() => {
    // TODO: fetch PO lines from API
    setLines([
      { po_line_id:'POL-0001', desc:'Acero A36', po_qty:1000 },
      { po_line_id:'POL-0002', desc:'Anclaje M20', po_qty:12 }
    ]);
  }, [poId]);

  async function submit(){
    const payload = { project_id: 42, po_id: poId, lines: Object.entries(qty).map(([po_line_id, q]) => ({ po_line_id, qty_received: q })) };
    const r = await fetch('/api/grn', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    if(!r.ok){ const e = await r.json(); alert(`${e.error}: ${e.detail}`); return; }
    alert('Recepción guardada');
  }

  return (
    <div className="rounded-2xl border p-4 space-y-3">
      <div className="text-sm text-neutral-600">Recepción rápida para {poId}</div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-neutral-500">
            <th className="p-2">Línea</th><th className="p-2">Descripción</th><th className="p-2">PO Qty</th><th className="p-2">Recibir</th>
          </tr>
        </thead>
        <tbody>
          {lines.map(l => (
            <tr key={l.po_line_id} className="border-t">
              <td className="p-2">{l.po_line_id}</td>
              <td className="p-2">{l.desc}</td>
              <td className="p-2">{l.po_qty}</td>
              <td className="p-2">
                <input type="number" min={0} className="border p-1 rounded w-32" onChange={e=>setQty({...qty,[l.po_line_id]:parseFloat(e.target.value)})} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button className="border px-3 py-1 rounded" onClick={submit}>Guardar recepción</button>
    </div>
  );
}
```

### 13.2 `ThreeWayBadge.tsx`
```tsx
'use client';
import React from 'react';

export default function ThreeWayBadge({ status }:{ status:'matching'|'under_received'|'over_received'|'invoice_over_receipt' }){
  const label = {
    matching: 'OK 3-way',
    under_received: 'Falta recepción',
    over_received: 'Sobre recepción',
    invoice_over_receipt: 'Factura > Recepción'
  }[status];
  return <span className="text-xs px-2 py-1 rounded-full border" title="Estado 3-way">{label}</span>;
}
```

### 13.3 `SubcontractCard.tsx`
```tsx
import React from 'react';

export default function SubcontractCard({ s }:{ s:{contract_id:number; contratado:number; certificado:number; pagado:number; retenido:number} }){
  const pct = (a:number,b:number)=> b>0 ? Math.round((a/b)*100) : 0;
  return (
    <div className="rounded-2xl border p-4">
      <div className="text-sm text-neutral-500">Contrato #{s.contract_id}</div>
      <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
        <div>Contratado</div><div className="text-right">{s.contratado.toLocaleString()}</div>
        <div>Certificado</div><div className="text-right">{s.certificado.toLocaleString()} ({pct(s.certificado,s.contratado)}%)</div>
        <div>Pagado</div><div className="text-right">{s.pagado.toLocaleString()}</div>
        <div>Retenido</div><div className="text-right">{s.retenido.toLocaleString()}</div>
      </div>
    </div>
  );
}
```

### 13.4 `CertificateWizard.tsx`
```tsx
'use client';
import React, { useState } from 'react';

export default function CertificateWizard({ contractId }:{ contractId:number }){
  const [lines, setLines] = useState<{contract_scope_id:number; qty_measured:number; amount:number}[]>([]);
  const [retPct, setRetPct] = useState(0.05);

  async function submit(){
    const payload = { period_start:'2025-09-01', period_end:'2025-09-30', retention_pct: retPct, lines, amortize_advances:true };
    const r = await fetch(`/api/contracts/${contractId}/certificate`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    const j = await r.json();
    if(!r.ok){ alert(j.detail||j.error); return; }
    alert(`Certificado ${j.certificate_id} neto ${j.net_payable.toLocaleString()}`);
  }

  return (
    <div className="rounded-2xl border p-4 space-y-3">
      <div className="text-sm text-neutral-600">Certificar contrato #{contractId}</div>
      <button className="border px-3 py-1 rounded" onClick={()=>setLines([{contract_scope_id:901, qty_measured:120, amount:4800000}])}>Cargar ejemplo</button>
      <div>
        Retención % <input className="border p-1 rounded w-24" type="number" step="0.01" value={retPct} onChange={e=>setRetPct(parseFloat(e.target.value))} />
      </div>
      <button className="border px-3 py-1 rounded" onClick={submit}>Calcular y guardar</button>
    </div>
  );
}
```

### 13.5 `SupplierPortalPage.tsx` (pública por token)
```tsx
'use client';
import React, { useEffect, useState } from 'react';

export default function SupplierPortalPage({ token }:{ token:string }){
  const [summary, setSummary] = useState<any>();
  const [invoices, setInvoices] = useState<any[]>([]);
  useEffect(()=>{
    (async()=>{
      const s = await fetch(`/api/supplier-portal/${token}/summary`).then(r=>r.json());
      const i = await fetch(`/api/supplier-portal/${token}/invoices`).then(r=>r.json());
      setSummary(s); setInvoices(i.items||[]);
    })();
  },[token]);
  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <h1 className="text-2xl font-semibold">Portal de Pagos — Proveedor</h1>
      {summary && (
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-2xl border p-3">OC abiertas: {summary.open_pos}</div>
          <div className="rounded-2xl border p-3">Por cobrar: {summary.to_be_paid}</div>
        </div>
      )}
      <div className="rounded-2xl border">
        <table className="w-full text-sm">
          <thead><tr className="text-left text-neutral-500"><th className="p-2">Factura</th><th className="p-2">PO</th><th className="p-2">Proyecto</th><th className="p-2">Monto</th><th className="p-2">Estado</th><th className="p-2">Vence/Pagada</th></tr></thead>
          <tbody>
            {invoices.map((x:any)=> (
              <tr key={x.invoice_id} className="border-t">
                <td className="p-2">#{x.invoice_id}</td>
                <td className="p-2">{x.po_id}</td>
                <td className="p-2">{x.project}</td>
                <td className="p-2">{Number(x.amount_total).toLocaleString()}</td>
                <td className="p-2">{x.status}</td>
                <td className="p-2">{x.paid_date || x.due_date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

---

## 14) **Notas para Copilot** (implementación)
- Mantener **Ley de Puertos** (UI 3001, API 5555) y **DB Canónica** (vistas/tablas autorizadas).  
- Todas las reglas críticas retornan **422** con `{error, detail, ...}` y dejan trazabilidad en bitácora.  
- **FK** reales en Postgres; en SQLite emular con validaciones.  
- Recalcular **cashflow expected** al: (a) crear GRN o devolución, (b) certificar subcontrato, (c) liberar retención.  
- UI: semáforos claros (3‑way), accesible móvil (portal proveedor).  
- Seguridad: tokens del portal con expiración; CORS sólo dominios permitidos.  
- Testing: unit (reglas), integración (GRN→Factura), E2E (portal proveedor).

---

## 15) **Anexo iConstruye** — Subcontratos EP (Espejo)
> Replicamos la estructura de los EP de subcontratistas vistos (carátula con % avance, resumen financiero del período con retención/anticipo/IVA, detalle de obra por ítem, y “historia del contrato” con acumulados). A continuación van **DDL mínimos**, **vistas** (SQLite + notas Postgres) y **endpoints** para imprimir/exportar.

### 15.1 DDL mínimos (si no existen)
```sql
-- Deducciones específicas por certificado de subcontrato
CREATE TABLE IF NOT EXISTS progress_certificate_deductions (
  id INTEGER PRIMARY KEY,
  certificate_id INTEGER NOT NULL,   -- FK a progress_certificates.id
  type TEXT CHECK (type IN ('retention','advance_amortization','penalty','other')) NOT NULL,
  description TEXT,
  amount REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_pcd_cert ON progress_certificate_deductions(certificate_id);
```
> **Postgres**: usar `BIGINT IDENTITY`, `NUMERIC(18,2)`, FK explícita a `progress_certificates(id)`.

### 15.2 Vistas — **Header** del EP (carátula + KPIs)
```sql
-- Paramétrica: IVA (dejar en 0.19 si no hay tabla de configuración)
DROP VIEW IF EXISTS v_cfg_tax;
CREATE VIEW v_cfg_tax AS SELECT 0.19 AS vat_rate;

-- Total contrato (scope)
DROP VIEW IF EXISTS v_contract_total_scope;
CREATE VIEW v_contract_total_scope AS
SELECT contract_id, SUM(qty * unit_price) AS total_scope
FROM contract_scope GROUP BY contract_id;

-- Monto período del certificado (bruto, sin deducciones)
DROP VIEW IF EXISTS v_pc_gross_period;
CREATE VIEW v_pc_gross_period AS
SELECT l.certificate_id, SUM(l.amount) AS gross_period, SUM(l.qty_measured) AS qty_period
FROM progress_certificate_lines l
GROUP BY l.certificate_id;

-- Deducciones por certificado (sumas por tipo)
DROP VIEW IF EXISTS v_pc_deductions;
CREATE VIEW v_pc_deductions AS
SELECT 
  d.certificate_id,
  SUM(CASE WHEN d.type='retention' THEN d.amount ELSE 0 END) AS retention,
  SUM(CASE WHEN d.type='advance_amortization' THEN d.amount ELSE 0 END) AS advance_amort,
  SUM(CASE WHEN d.type IN ('penalty','other') THEN d.amount ELSE 0 END) AS other_deductions
FROM progress_certificate_deductions d
GROUP BY d.certificate_id;

-- Acumulado certificado a la fecha (monto bruto)
DROP VIEW IF EXISTS v_pc_cum_to_date;
CREATE VIEW v_pc_cum_to_date AS
SELECT pc.contract_id, pc.id AS certificate_id,
       (
         SELECT COALESCE(SUM(l2.amount),0)
         FROM progress_certificate_lines l2
         JOIN progress_certificates pc2 ON pc2.id = l2.certificate_id
         WHERE pc2.contract_id = pc.contract_id
           AND (pc2.approved_at IS NOT NULL AND pc2.approved_at <= COALESCE(pc.approved_at, pc.created_at))
       ) AS gross_cum
FROM progress_certificates pc;

-- HEADER EP: carátula + KPIs
DROP VIEW IF EXISTS v_subcontract_ep_header;
CREATE VIEW v_subcontract_ep_header AS
SELECT 
  pc.id AS certificate_id,
  pc.contract_id,
  c.project_id,
  pc.period_start, pc.period_end,
  pc.approved_at,
  COALESCE(pc.retention_pct, c.retention_pct, 0.0) AS retention_pct,
  ts.total_scope AS contract_total,
  gp.gross_period,
  COALESCE(d.retention, gp.gross_period * COALESCE(pc.retention_pct, c.retention_pct, 0.0)) AS retention_period,
  COALESCE(d.advance_amort, 0) AS advance_amortization,
  COALESCE(d.other_deductions, 0) AS other_deductions,
  (gp.gross_period - COALESCE(d.retention, gp.gross_period * COALESCE(pc.retention_pct, c.retention_pct, 0.0)) - COALESCE(d.advance_amort,0) - COALESCE(d.other_deductions,0)) AS net_payable,
  cfg.vat_rate,
  ROUND((gp.gross_period - COALESCE(d.retention, gp.gross_period * COALESCE(pc.retention_pct, c.retention_pct, 0.0)) - COALESCE(d.advance_amort,0) - COALESCE(d.other_deductions,0)) * cfg.vat_rate, 2) AS vat_amount,
  ROUND((gp.gross_period - COALESCE(d.retention, gp.gross_period * COALESCE(pc.retention_pct, c.retention_pct, 0.0)) - COALESCE(d.advance_amort,0) - COALESCE(d.other_deductions,0)) * (1+cfg.vat_rate), 2) AS gross_with_tax,
  cum.gross_cum AS certified_cumulative,
  CASE WHEN ts.total_scope > 0 THEN ROUND(100.0 * cum.gross_cum / ts.total_scope, 2) ELSE 0 END AS physical_progress_pct
FROM progress_certificates pc
JOIN contracts c ON c.id = pc.contract_id
LEFT JOIN v_contract_total_scope ts ON ts.contract_id = c.id
LEFT JOIN v_pc_gross_period gp ON gp.certificate_id = pc.id
LEFT JOIN v_pc_deductions d ON d.certificate_id = pc.id
LEFT JOIN v_pc_cum_to_date cum ON cum.certificate_id = pc.id
CROSS JOIN v_cfg_tax cfg;
```
> **Notas Postgres**: usar `numeric`, `coalesce`, `date_trunc` si quieres buckets; las subconsultas válidas tal cual.

### 15.3 Vistas — **Detalle** de obra (origen / EP anterior / período / pendiente)
```sql
-- Sumas por item en certificados previos al actual
DROP VIEW IF EXISTS v_pc_prev_item_sums;
CREATE VIEW v_pc_prev_item_sums AS
SELECT 
  pc.id AS certificate_id,
  cs.id AS contract_scope_id,
  (
    SELECT COALESCE(SUM(l2.qty_measured),0)
    FROM progress_certificate_lines l2
    JOIN progress_certificates pc2 ON pc2.id = l2.certificate_id
    WHERE pc2.contract_id = pc.contract_id
      AND l2.contract_scope_id = cs.id
      AND (pc2.approved_at IS NOT NULL AND pc2.approved_at < COALESCE(pc.approved_at, pc.created_at))
  ) AS qty_prev,
  (
    SELECT COALESCE(SUM(l2.amount),0)
    FROM progress_certificate_lines l2
    JOIN progress_certificates pc2 ON pc2.id = l2.certificate_id
    WHERE pc2.contract_id = pc.contract_id
      AND l2.contract_scope_id = cs.id
      AND (pc2.approved_at IS NOT NULL AND pc2.approved_at < COALESCE(pc.approved_at, pc.created_at))
  ) AS amount_prev
FROM progress_certificates pc
JOIN contract_scope cs ON cs.contract_id = pc.contract_id;

-- Sumas por item EN el certificado actual
DROP VIEW IF EXISTS v_pc_curr_item_sums;
CREATE VIEW v_pc_curr_item_sums AS
SELECT l.certificate_id, l.contract_scope_id,
       COALESCE(SUM(l.qty_measured),0) AS qty_curr,
       COALESCE(SUM(l.amount),0) AS amount_curr
FROM progress_certificate_lines l
GROUP BY l.certificate_id, l.contract_scope_id;

-- DETALLE estilo iConstruye
DROP VIEW IF EXISTS v_subcontract_ep_lines;
CREATE VIEW v_subcontract_ep_lines AS
SELECT 
  pc.id AS certificate_id,
  cs.id AS contract_scope_id,
  cs.item_code,
  cs.description,
  cs.unit,
  cs.qty   AS qty_origin,
  cs.unit_price,
  (cs.qty * cs.unit_price) AS amount_origin,
  COALESCE(prev.qty_prev,0)     AS qty_prev,
  COALESCE(prev.amount_prev,0)  AS amount_prev,
  COALESCE(curr.qty_curr,0)     AS qty_period,
  COALESCE(curr.amount_curr,0)  AS amount_period,
  (cs.qty - COALESCE(prev.qty_prev,0) - COALESCE(curr.qty_curr,0))      AS qty_pending,
  ((cs.qty * cs.unit_price) - COALESCE(prev.amount_prev,0) - COALESCE(curr.amount_curr,0)) AS amount_pending
FROM progress_certificates pc
JOIN contract_scope cs ON cs.contract_id = pc.contract_id
LEFT JOIN v_pc_prev_item_sums prev  ON prev.certificate_id = pc.id AND prev.contract_scope_id = cs.id
LEFT JOIN v_pc_curr_item_sums curr  ON curr.certificate_id = pc.id AND curr.contract_scope_id = cs.id;
```

### 15.4 Vista — **Historia** del contrato (acumulados por EP)
```sql
DROP VIEW IF EXISTS v_subcontract_ep_history;
CREATE VIEW v_subcontract_ep_history AS
SELECT 
  pc.contract_id,
  pc.id AS certificate_id,
  pc.period_start, pc.period_end, pc.approved_at,
  gp.gross_period,
  COALESCE(d.retention, gp.gross_period * COALESCE(pc.retention_pct, 0)) AS retention_period,
  COALESCE(d.advance_amort, 0) AS advance_amortization,
  COALESCE(d.other_deductions, 0) AS other_deductions,
  (gp.gross_period - COALESCE(d.retention, gp.gross_period * COALESCE(pc.retention_pct, 0)) - COALESCE(d.advance_amort,0) - COALESCE(d.other_deductions,0)) AS net_payable
FROM progress_certificates pc
LEFT JOIN v_pc_gross_period gp ON gp.certificate_id = pc.id
LEFT JOIN v_pc_deductions d ON d.certificate_id = pc.id
ORDER BY pc.contract_id, COALESCE(pc.approved_at, pc.created_at);
```
> Esta vista alimenta el **anexo** que lista cada EP con *monto EP*, *retención*, *amortización de anticipo*, *descuentos* y *neto pagable*, además de totales.

### 15.5 Endpoints (5555) para imprimir/exportar EP de subcontrato
```yaml
# OpenAPI (resumen)
paths:
  /api/contracts/{id}/certificates/{ep_id}/header:
    get: { summary: Header EP (KPIs), responses: { '200': { description: OK }}}
  /api/contracts/{id}/certificates/{ep_id}/lines:
    get: { summary: Detalle EP (líneas), responses: { '200': { description: OK }}}
  /api/contracts/{id}/ep-history:
    get: { summary: Historia del contrato por EP, responses: { '200': { description: OK }}}
  /api/contracts/{id}/certificates/{ep_id}/export.pdf:
    post: { summary: Exportar PDF espejo iConstruye, responses: { '200': { description: PDF generado }}}
  /api/contracts/{id}/certificates/{ep_id}/export.xlsx:
    post: { summary: Exportar XLSX espejo iConstruye, responses: { '200': { description: XLSX generado }}}
```
**Notas de implementación**
- El **PDF** utiliza `v_subcontract_ep_header` (carátula/resumen) + `v_subcontract_ep_lines` (detalle) + `v_subcontract_ep_history` (anexo).  
- Mantener numeración de EP, fechas y % retención en el header.  
- El **XLSX** replica columnas: *Código, Descripción, UM, Cantidad Contratada, PU, Ejecutado Origen, EP Anterior, Período, Pendiente (cant/monto)*.

### 15.6 Wizard de importación “EP Subcontratista (iConstruye‑like)”
- **Sugerencias de columnas** (matching difuso):
  - `item_code`: ["Código", "Ítem", "Item"],
  - `description`: ["Descripción", "Desc"],
  - `unit`: ["UM", "Unidad"],
  - `qty_origin`: ["Cant. Contratada", "Cantidad Contratada"],
  - `unit_price`: ["PU", "Precio Unitario"],
  - `qty_prev` / `amount_prev`: ["EP Anterior Cant", "EP Anterior Monto"],
  - `qty_period` / `amount_period`: ["Período Cant", "Período Monto", "Mes"].
- **Validaciones**: por ítem `prev+period ≤ origin`; a nivel contrato `acum ≤ total_scope`.  
- **Resultado**: generar `progress_certificate_lines` con `amount_period` (o `qty_period*unit_price` si viene vacío) y `progress_certificate_deductions` (retención, anticipo, multas).

### 15.7 UI — pestañas de EP (Subcontratos)
- **Carátula**: % avance físico, bruto/retención/anticipo/descuentos/neto, más badges de validación.  
- **Detalle**: tabla estilo iConstruye con *origen / EP anterior / período / pendiente* (cantidades y montos).  
- **Historia**: lista de EP con acumulados y totales; botón **Exportar PDF/XLSX**.


---

## 16) **Insights desde HAR (Zoho Books)** — Qué replicar en Ofitec
> Analicé tus `.har` de **Proyecto/Proveedores/OC** (Zoho Books WebApp). Hay patrones muy valiosos para endurecer nuestro 3‑way match, el ciclo AP y la UX. Abajo dejo **qué vimos** y **cómo lo implementamos** ya alineado a *DB Canónica* y a lo que venimos construyendo.

### 16.1 Qué vimos en los HAR (resumen)
- **Hosts**: `books.zoho.com` (API v3). Endpoints consultados: `projects`, `purchaseorders`, `bills`, `vendorpayments`, `expenses`, `salesorders`, `estimates`, `tasks`, `chatlets`.
- **Query params estándar**: `page`, `per_page`, `sort_column=date`, `sort_order=D`, `project_id`, `organization_id`, `txn=true` (pide totales).  
- **PO** (list): traen múltiples **estados paralelos** (`order_status`, `billed_status`, `received_status`, `status`), `due_in_days`, `currency`, `price_precision`, **custom fields** (`cf_cat_1..4`), flags de recepción (`is_po_marked_as_received`), y `receives` (histórico).  
- **Bills (AP)**: `status=pending_approval`, `reference_number` (amarrado a PO), `balance_due`, y un flag clave: **`is_bill_reconciliation_violated`** (idéntico al semáforo que queremos).  
- **Vendor Payments**: `payment_mode` (Cheque/Transferencia), `payment_number`, `paid_through_account_name`, `date`, `amount`, `bcy_amount` (moneda base), `reference_number` (banco).  
- **Projects**: metadata de cliente, `rate`, `users_working`, y `custom_fields` vacíos (en tu tenant actual).

---

### 16.2 Cambios recomendados en Ofitec (modelo y vistas)
**A) Estados paralelos en OC (evita sobrecargar un solo `status`)**
```sql
-- Si ya existe purchase_orders_unified, crear vista extendida
DROP VIEW IF EXISTS v_po_status_enhanced;
CREATE VIEW v_po_status_enhanced AS
SELECT
  po.*,  -- campos actuales canónicos
  /* estados paralelos, derivables de eventos/vistas */
  CASE WHEN po.total_billed >= po.total THEN 'billed' ELSE 'unbilled' END AS billed_status,
  CASE WHEN po.total_received_qty >= po.total_ordered_qty THEN 'received' ELSE 'partial' END AS received_status,
  /* substatus compuesto para UI (no contractual) */
  CASE
    WHEN po.cancelled_at IS NOT NULL THEN 'cancelled'
    WHEN po.total_billed >= po.total AND po.total_received_qty >= po.total_ordered_qty THEN 'closed'
    WHEN po.total_billed = 0 AND po.total_received_qty = 0 THEN 'open'
    ELSE 'in_progress'
  END AS order_status
FROM purchase_orders_unified po;
```
**B) Semáforo tipo `is_bill_reconciliation_violated`**
```sql
DROP VIEW IF EXISTS v_ap_reconciliation_flags;
CREATE VIEW v_ap_reconciliation_flags AS
SELECT
  il.invoice_id,
  il.po_line_id,
  /* reglas duras */
  (CASE WHEN il.qty > rec.qty_received_accum THEN 1 ELSE 0 END) AS invoice_over_receipt,
  (CASE WHEN (il.qty * il.unit_price) > pol.qty * pol.unit_price THEN 1 ELSE 0 END) AS invoice_over_po,
  /* resumen */
  (CASE WHEN (il.qty > rec.qty_received_accum) OR ((il.qty*il.unit_price) > (pol.qty*pol.unit_price)) THEN 1 ELSE 0 END) AS is_bill_reconciliation_violated
FROM invoice_lines il
JOIN purchase_order_lines pol ON pol.po_line_id = il.po_line_id
LEFT JOIN v_po_line_received_accum rec ON rec.po_line_id = il.po_line_id;
```
**C) Dimensiones/etiquetas (cf_cat_1..4)**  
Agregar `po_tags`/`ap_tags` (o mapear a `categories`/centros de costo). Se usan luego para **reportes** y filtros.

**D) Pagos a proveedor (ledger mínimo)**  
Campos que conviene guardar en `ap_payments`: `payment_mode`, `payment_number`, `paid_through_account_id|name`, `reference_number` (banco), `bcy_amount` (moneda base), `currency_code`.

---

### 16.3 API 5555 — compatibilidad de filtros
Replicar los patrones `page/per_page/sort_column/sort_order/project_id/txn=true`:
```http
GET /api/purchaseorders?page=1&per_page=20&sort_column=date&sort_order=D&project_id=42&txn=true
GET /api/bills?page=1&per_page=20&sort_column=date&sort_order=D&project_id=42&txn=true
GET /api/vendorpayments?page=1&per_page=20&sort_column=date&sort_order=D&project_id=42
```
**Respuesta** incluir `page_context` (total, has_more_page, page, per_page) para que la UI pagine igual de fluido que Zoho.

---

### 16.4 UX concreta que vale la pena copiar
1) **Tarjetas con estados paralelos en OC**: mostrar **`order_status`**, **`received_status`**, **`billed_status`** (tres chips). Así el usuario ve en qué eslabón está el problema.  
2) **Badge de conciliación** en facturas: `OK` / `Factura > OC` / `Factura > Recepción` (usando `v_ap_reconciliation_flags`).  
3) **Filtros por proyecto + orden**: persistir `sort_column=date` y `D/A`.  
4) **Pagos**: mostrar **modo** (Cheque/Transferencia), **cuenta pagadora** y **n° de pago**; es información clave que Zoho expone y los proveedores preguntan.  
5) **Adjuntos/`has_attachment`**: icono clip en PO/Bill/Payment y link al Drive.

---

### 16.5 Portal Proveedor — pipeline estilo Zoho (pero simplificado)
- **Lista**: Facturas → estado (emitida/aprobación/pagada), `due_date`, `amount_total`, y **fecha de pago** si ya conciliada.  
- **Detalle**: timeline **PO → GRN → Bill → Payment** con validaciones (3‑way) y adjuntos.  
- **KPIs**: `to_be_paid`, `last_payment {amount,date}` — mismos numeritos que se ven en Zoho.

---

### 16.6 Controles adicionales inspirados en Zoho
- **`pending_approval`** en Bills (maker–checker).  
- **`due_in_days`** y **`balance_due`** calculados y visibles.  
- **`price_precision`** por moneda (definir a nivel `currency`).  
- **`client_viewed_time`** → nuestro `supplier_viewed_time` (token portal) para trazar si el proveedor vio la OC o la programación de pago.  
- **`recurringbills/recurringexpenses`**: no implementarlos aún, pero dejar **flags** para soportarlos (un buen “futuro cercano”).

---

### 16.7 Acciones para Copilot (directas)
- Crear `v_po_status_enhanced` y `v_ap_reconciliation_flags` (SQLite + Postgres).  
- Extender `/api/*` con `page_context` y filtros (`sort_*`, `project_id`, `txn`).  
- UI: chips de estado paralelos en OC; badge de conciliación en Bills; tabla de pagos con `payment_mode/number/account`.  
- Portal Proveedor: sumar KPIs y timeline PO→GRN→Bill→Payment; exponer adjuntos.

> Con esto, cerramos la brecha funcional con lo bueno de Zoho **sin integrar** nada: sólo copiamos lo que agrega valor a la operación y a la transparencia con proveedores.

