# OFITEC — Playbook **Estados de Pago (Cliente)**

**Objetivo:** Registrar en Ofitec los **Estados de Pago (EP)** aprobados por el **cliente** (no confundir con certificados de subcontratistas) para que desde ahí se **genere la facturación de venta (AR)**, se alimente el **Flujo de Caja (inflows)** y se controle el **avance comercial** del proyecto.

> Los EP normalmente se negocian en Excel y con formatos impuestos por el cliente. Ofitec debe **importarlos** (tolerante a formatos), consolidarlos y conectarlos con **ventas/facturación/cobranzas**.

---

## 1) Conceptos y alcance

- **EP Cliente**: documento mensual (o por hito) que resume avance para **cobro al cliente**. Puede contener líneas por ítem/capítulo con cantidad, PU y monto **del período** y **acumulado**.
- **No es lo mismo** que el **certificado del subcontratista** (costos). EP impacta **ingresos**.
- **Resultado esperado**: desde un EP **aprobado** se genera la **factura de venta** y el **inflow esperado** del cashflow.

---

## 2) Modelo de datos (mínimo viable robusto)

> SQLite flavor (TEXT fechas). Incluir índices e integridad. Para Postgres, usar DATE/NUMERIC/IDENTITY.

### 2.1 Contrato con cliente / Schedule of Values (opcional pero recomendado)

```sql
CREATE TABLE IF NOT EXISTS client_contracts (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL,
  customer_id INTEGER NOT NULL,
  code TEXT,           -- código contrato externo
  start_date TEXT, end_date TEXT,
  currency TEXT,
  payment_terms_days INTEGER DEFAULT 30,
  retention_pct REAL DEFAULT 0,
  status TEXT CHECK (status IN ('active','closed')) DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS client_sov_items (
  id INTEGER PRIMARY KEY,
  contract_id INTEGER NOT NULL,
  item_code TEXT,         -- código del cliente
  description TEXT,
  unit TEXT,
  qty REAL,
  unit_price REAL,
  line_total REAL,
  chapter TEXT,           -- opcional: agrupador de reporte
  UNIQUE(contract_id, item_code)
);
```

### 2.2 Estados de Pago (EP) Cliente

```sql
CREATE TABLE IF NOT EXISTS ep_headers (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL,
  contract_id INTEGER,
  ep_number TEXT,                 -- correlativo interno/externo
  period_start TEXT, period_end TEXT,
  submitted_at TEXT, approved_at TEXT,
  status TEXT CHECK (status IN ('draft','submitted','approved','rejected','invoiced','paid')) DEFAULT 'draft',
  retention_pct REAL,             -- si difiere del contrato
  notes TEXT
);

CREATE TABLE IF NOT EXISTS ep_lines (
  id INTEGER PRIMARY KEY,
  ep_id INTEGER NOT NULL,
  sov_item_id INTEGER,            -- si hay contrato/SOV
  item_code TEXT,                 -- si no hay contrato, usar código del cliente
  description TEXT,
  unit TEXT,
  qty_period REAL,
  unit_price REAL,
  amount_period REAL,             -- = qty_period * unit_price (o importado)
  qty_cum REAL,                   -- acumulado
  amount_cum REAL,
  chapter TEXT
);

CREATE TABLE IF NOT EXISTS ep_deductions (
  id INTEGER PRIMARY KEY,
  ep_id INTEGER NOT NULL,
  type TEXT CHECK (type IN ('retention','advance_amortization','penalty','other')),
  description TEXT,
  amount REAL NOT NULL
);

-- Vínculo con archivos (Excel/PDF) subidos y versión aprobada
CREATE TABLE IF NOT EXISTS ep_files (
  id INTEGER PRIMARY KEY,
  ep_id INTEGER NOT NULL,
  drive_file_id TEXT, storage_url TEXT,
  kind TEXT CHECK (kind IN ('xlsx','pdf')),
  uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### 2.3 Facturación y cobranzas (AR) generadas desde EP

> Si ya existen tablas/vistas AR, solo enlazar por `ep_id`. Caso contrario:

```sql
CREATE TABLE IF NOT EXISTS ar_invoices (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL,
  customer_id INTEGER NOT NULL,
  ep_id INTEGER,                 -- vínculo directo EP→Factura
  invoice_number TEXT,
  invoice_date TEXT,
  due_date TEXT,
  amount_net REAL,
  tax_amount REAL,
  amount_total REAL,
  status TEXT CHECK (status IN ('draft','issued','paid','cancelled')) DEFAULT 'issued'
);

CREATE TABLE IF NOT EXISTS ar_collections (
  id INTEGER PRIMARY KEY,
  invoice_id INTEGER NOT NULL,
  collected_date TEXT,
  amount REAL,
  method TEXT,
  bank_ref TEXT
);
```

---

## 3) Importador de EP (Excel tolerante a formato)

- **Entrada**: XLSX (o CSV) con cabecera y líneas. El cliente puede imponer columnas/códigos.
- **Plantillas/sugerencias** (`ideas/ep_import_templates.json`):
  - **header\_map**: { "ep\_number": ["Nº EP","EP","N\_Estado"], "period\_start": ["Desde","Inicio"], "period\_end": ["Hasta","Término"]… }
  - **line\_map**: { "item\_code":["Código","Ítem"], "description":["Descripción"], "unit":["Unidad"], "qty\_period":["Cant. Mes"], "unit\_price":["PU"], "amount\_period":["Monto Mes"], "qty\_cum":["Acum Cant"], "amount\_cum":["Acum Monto"], "chapter":["Capítulo"] }
- **Matching difuso** + **modo interactivo** (CLI o UI) cuando haya ambigüedad.
- **Validaciones**:
  - Si hay **client\_contracts/SOV**: `amount_cum` por ítem **≤** `line_total` del contrato.
  - `amount_period` **≤** saldo del item (line\_total − amount\_cum\_prev).
  - Sumatoria `amount_period` − deducciones ≥ 0.
- **Staging & auditoría**: tabla temporal `ep_import_staging` + log de decisiones de mapeo.

---

## 4) Reglas de negocio y workflow

1. **Draft → Submitted → Approved** (fecha de aprobación = `approved_at`).
2. **EP aprobado → Generar Factura AR**:
   - Base imponible = Σ `amount_period` (líneas) − Σ `deductions` (que correspondan). IVA según política.
   - `invoice_date` = `approved_at`; `due_date` = `invoice_date` + `payment_terms_days` (contrato/cliente).
   - Estado factura: `issued`. Se crea vínculo `ar_invoices.ep_id = EP.id`.
3. **Cobranza**: registrar pagos en `ar_collections`; **nunca cobrar > factura** (validación dura).
4. **Retención**: si aplica, llevar **ledger** por proyecto/contrato y definir política de liberación (ej.: recepción final + 30 días) → genera **inflow esperado futuro**.

---

## 5) Vistas canónicas (resumen y cashflow de ingresos)

```sql
-- EP aprobados por proyecto (monto del período, neto sin IVA)
DROP VIEW IF EXISTS v_ep_approved_project;
CREATE VIEW v_ep_approved_project AS
SELECT h.project_id, strftime('%Y-%m-01', h.approved_at) AS bucket_month,
       SUM(l.amount_period) - COALESCE((
         SELECT SUM(d.amount) FROM ep_deductions d WHERE d.ep_id = h.id
       ),0) AS ep_amount_net
FROM ep_headers h
JOIN ep_lines l ON l.ep_id = h.id
WHERE h.status IN ('approved','invoiced','paid')
GROUP BY h.project_id, bucket_month;

-- Facturas AR emitidas desde EP (para inflows expected si aún no cobrado)
DROP VIEW IF EXISTS v_ar_expected_project;
CREATE VIEW v_ar_expected_project AS
SELECT a.project_id,
       strftime('%Y-%m-01', a.due_date) AS bucket_month,
       SUM(a.amount_total) - COALESCE((
         SELECT SUM(c.amount) FROM ar_collections c WHERE c.invoice_id = a.id
       ),0) AS expected_inflow
FROM ar_invoices a
WHERE a.status IN ('issued')
GROUP BY a.project_id, bucket_month;

-- Cobros reales (actual inflows)
DROP VIEW IF EXISTS v_ar_actual_project;
CREATE VIEW v_ar_actual_project AS
SELECT a.project_id, strftime('%Y-%m-01', c.collected_date) AS bucket_month,
       SUM(c.amount) AS actual_inflow
FROM ar_collections c
JOIN ar_invoices a ON a.id = c.invoice_id
GROUP BY a.project_id, bucket_month;
```

> **Cashflow consolidado**: sumar `expected_inflow` de AR con `expected_outflow` de compras (ya definido) para el neto mensual.

---

## 6) API (5555) — contratos clave

- `GET /api/projects/:id/ep` → lista de EP (status, período, montos, enlace a archivos).
- `POST /api/ep/import` → subir XLSX/CSV con mapping interactivo (guardar `ep_header`, `ep_lines`, `ep_deductions`).
- `POST /api/ep/:id/approve` → valida y marca `approved_at`.
- `POST /api/ep/:id/generate-invoice` → crea `ar_invoices` con `due_date` según términos.
- `GET /api/projects/:id/finance` → **agregar** `ar_from_ep` (emitidas) y `ep_pending_invoice` (aprobadas no facturadas).

**Errores 422**: `ep_exceeds_contract_item`, `invoice_over_ep`, `over_collected`.

---

## 7) UI/UX — Proyecto ▸ Tab “Ventas / EP”

- **Header**: total EP aprobados (mes y acumulado), **backlog por cobrar**, aging de AR.
- **Tabla EP**: Nº, período, estado, monto período, deducciones, neto, IVA, total, fechas, **badge** (aprobado/emitido/pagado), botón **Generar factura** si corresponde.
- **Detalle EP**: líneas por capítulo/ítem; comparador con EP anterior (differences ↑/↓).
- **Importar EP**: dropzone XLSX → wizard de mapeo (detectar columnas) → vista previa → guardar.
- **Acciones IA**:
  - validar consistencia (líneas sin código, % variaciones raras),
  - resumir cambios vs mes anterior,
  - redactar correo a cliente con resumen y adjuntos (link Drive).

---

## 8) Integración con Drive y WhatsApp

- **Drive**: guardar Excel/PDF firmado; exponer enlace en ep\_files. Indexar texto para búsqueda.
- **WhatsApp**: hilo por EP/cliente; plantillas de envío/recordatorio; registrar acuses y compromisos de pago.

---

## 9) Validaciones y políticas

- **EP ≤ Contrato/SOV** por ítem (si existe). Si no hay contrato cargado, permitir con **warning** y **flag**.
- **Factura ≤ EP (neto/total)**. **Cobro ≤ Factura**.
- **Retención**: llevar saldo y política de liberación (genera inflow futuro cuando corresponda).

---

## 10) Reportes y analítica

- **Curva S de ingresos**: acumulado de EP vs ventas contratadas.
- **Backlog:** ventas contratadas − EP aprobados.
- **KPIs**: % cobrado sobre facturado, días promedio de cobro, desviación EP vs plan comercial.

---

## 11) Plan de implementación (2 sprints)

**Sprint 1**

- Tab “Ventas/EP” básico: lista/import/approve/generar factura.
- Vistas `v_ep_approved_project`, `v_ar_expected_project`, `v_ar_actual_project`.
- Integración en `/api/projects/:id/finance` (inflows expected/actual) y en resumen 360.

**Sprint 2**

- Comparador EP vs EP (differences), aging AR, políticas de retención, IA de validación y redacción.
- Integración Drive/WhatsApp en EP.

---

## 12) Excel — columnas sugeridas (plantilla guía)

- **Header**: Nº EP, Proyecto, Cliente, Desde, Hasta, Fecha Aprobación, Retención %, Notas.
- **Lines**: Código Ítem (cliente), Descripción, Unidad, Cantidad Mes, PU, Monto Mes, Cantidad Acum, Monto Acum, Capítulo.
- **Deductions** (opcional): Tipo, Descripción, Monto.

---

## 13) Notas para Copilot

- Mantener integridad con **DB Canónica** y cohesión con módulo **Proyecto** y **Cashflow**.
- Respetar **Ley de Puertos** y exponer sólo **vistas/tablas autorizadas**.
- Importador tolerante con **matching difuso** y **modo asistido**.
- Todas las validaciones críticas → **422** con payload explicativo.
- Registrar vínculos a **Drive** y a **hilos WhatsApp** por EP.

