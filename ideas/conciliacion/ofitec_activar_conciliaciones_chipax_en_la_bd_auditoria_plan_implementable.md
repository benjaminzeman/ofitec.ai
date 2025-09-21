# OFITEC — **Activar conciliaciones Chipax** en la Base de Datos
> Auditoría del `chipax_data.db` incluido en tu ZIP + plan técnico para **aprovechar toda la conciliación** que ya trajiste desde Chipax (AP/AR/Gastos/Cartola) y que hoy no se refleja en Ofitec. Entrego **DDL**, **vistas canónicas**, **scripts de importación** y **checks de QA** para que Copilot lo implemente.

---

## 0) Hallazgos clave (radiografía)
**Lo que sí está:**
- Tablas base: `purchase_orders_unified`, `purchase_lines_unified`, `sales_invoices`, `bank_movements`, `vendors_unified`, `projects`, `proyectos`, etc.
- Vistas utilitarias reales: `v_cartola_bancaria`, `v_po_committed`, `v_presupuesto_totales`, `v_control_financiero_resumen`.
- Carpeta de **insumos Chipax conciliados** (CSV) en `data/raw/chipax/` con gran volumen:
  - `*_Facturas compra_conciliacion.csv` → **12.785** filas.
  - `*_Facturas venta_conciliacion.csv` → **1.215** filas.
  - `*banco*conciliacion.csv` → **20.696** movimientos bancarios.
  - `*_Gastos_conciliacion.csv` → **3.040** filas.

**Lo que falta / está mal hoy:**
- `v_facturas_compra` **apunta a PO** (no a facturas AP): es un *proxy* que devuelve compras desde `purchase_orders_unified`. Resultado: la conciliación sugiere contra PO en vez de contra **facturas**.
- **No existen tablas** para guardar **ap_invoices** (AP) ni **ap_invoice_lines**.
- **No existe** un registro canónico de **conciliaciones** (no hay `recon_*`).
- `v_cartola_bancaria` no muestra estado `conciliado` ni enlaces a documentos.
- Los **importadores** (`tools/import_bank_movements.py`, `create_finance_views.py`) no leen los CSV *conciliación* de Chipax.

**Conclusión:** tienes los datos **conciliados** (Chipax) pero **no se cargan** a la BD canónica ni a las vistas. Vamos a activarlos con un pipeline mínimo y seguro.

---

## 1) Modelo canónico propuesto (minimamente invasivo)
> Mantiene nombres de *docs_oficiales* y agrega lo mínimo que falta.

```sql
-- 1) Facturas de Compra (AP)
CREATE TABLE IF NOT EXISTS ap_invoices (
  id INTEGER PRIMARY KEY,
  vendor_rut TEXT,
  vendor_name TEXT,
  invoice_number TEXT,      -- Folio
  invoice_date TEXT,        -- Emisión
  due_date TEXT,
  currency TEXT DEFAULT 'CLP',
  net_amount REAL,
  tax_amount REAL,
  exempt_amount REAL,
  total_amount REAL,
  source_platform TEXT,     -- CHIPAX | SII | etc
  source_id TEXT,           -- id externo si existe
  project_name TEXT,        -- opcional (si viene)
  status TEXT,              -- open|paid|overdue|cancelled
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ap_invoice_lines (
  id INTEGER PRIMARY KEY,
  invoice_id INTEGER NOT NULL REFERENCES ap_invoices(id) ON DELETE CASCADE,
  description TEXT,
  qty REAL,
  unit_price REAL,
  line_total REAL,
  uom TEXT,
  po_id TEXT,               -- si mapeada a OC
  po_line_id TEXT
);

-- 2) Conciliación canónica (N↔M)
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
  bank_movement_id INTEGER,           -- FK bank_movements
  sales_invoice_id INTEGER,           -- FK sales_invoices
  ap_invoice_id INTEGER,              -- FK ap_invoices
  expense_id INTEGER,
  payroll_id INTEGER,
  tax_id INTEGER,
  amount REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_links_bank     ON recon_links(bank_movement_id);
CREATE INDEX IF NOT EXISTS idx_links_ap       ON recon_links(ap_invoice_id);
CREATE INDEX IF NOT EXISTS idx_links_sales    ON recon_links(sales_invoice_id);

-- 3) Staging crudo (opcional pero recomendado para auditoría)
CREATE TABLE IF NOT EXISTS chipax_raw_ap (id INTEGER PRIMARY KEY, row_json TEXT);
CREATE TABLE IF NOT EXISTS chipax_raw_ar (id INTEGER PRIMARY KEY, row_json TEXT);
CREATE TABLE IF NOT EXISTS chipax_raw_bank (id INTEGER PRIMARY KEY, row_json TEXT);
CREATE TABLE IF NOT EXISTS chipax_raw_expense (id INTEGER PRIMARY KEY, row_json TEXT);
```

**Índices sugeridos**
```sql
CREATE INDEX IF NOT EXISTS idx_bm_date ON bank_movements(fecha);
CREATE INDEX IF NOT EXISTS idx_bm_amount ON bank_movements(monto);
ALTER TABLE bank_movements ADD COLUMN IF NOT EXISTS descripcion_norm TEXT;
UPDATE bank_movements SET descripcion_norm = UPPER(REPLACE(glosa,'  ',' ')) WHERE descripcion_norm IS NULL;
CREATE INDEX IF NOT EXISTS idx_bm_norm ON bank_movements(descripcion_norm);
```

---

## 2) Importadores desde Chipax (conciliación)
> Nuevo script `tools/import_chipax_conciliacion.py` que **lee todos los CSV** de `data/raw/chipax/` y pobla staging + canónico.

### 2.1 Mapeos (AP)
Origen: `*_Facturas compra_conciliacion.csv`

| CSV Chipax | ap_invoices |
|---|---|
| `RUT` | `vendor_rut` |
| `Razón Social` | `vendor_name` |
| `Folio` | `invoice_number` |
| `Fecha Emisión` | `invoice_date` |
| `Fecha Vencimiento` | `due_date` |
| `Moneda` / `Tipo de Cambio (CLP)` | `currency` |
| `Monto Neto (CLP)` | `net_amount` |
| `Monto Exento (CLP)` | `exempt_amount` |
| `Monto IVA (CLP)` | `tax_amount` |
| `Monto Total (CLP)` | `total_amount` |
| (constante) `CHIPAX` | `source_platform` |

**Enlaces a cartola (reconciliación)**
- Si hay columnas `Banco`, `Id`, `Fecha`, `Abono/Cargo`, `Descripción` → crear una fila en `recon_reconciliations(context='purchase')` y una o más en `recon_links(ap_invoice_id=?, bank_movement_id=?, amount=...)`.
- Resolver `bank_movement_id` con *match* por (`bank_name`,`account_number`,`fecha`,`monto`,`glosa`) normalizados.

### 2.2 Mapeos (AR)
Origen: `*_Facturas venta_conciliacion.csv` → `sales_invoices` (ya existe). Agregar `source_platform='CHIPAX'` y, si corresponde, `project_id` vía `projects_analytic_map` o por alias de cliente.

### 2.3 Mapeos (Gastos)
Origen: `*_Gastos_conciliacion.csv` → `expenses` y `recon_links(expense_id↔bank_movement_id)`.

### 2.4 Mapeos (Cartola)
Origen: `*banco*conciliacion.csv` → completar/actualizar `bank_movements` (si faltan filas), y **reconstruir** enlaces si el CSV trae múltiples documentos por movimiento (split).

### 2.5 Notas de parsing
- Números: remover `$`, puntos de miles y usar `,` como decimal (ya tienes utilidades en `etl_common.py`).
- Fechas: `YYYY-MM-DD`.
- Monedas: mapear a ISO (`CLP`, `USD`).
- Tolerancia para *match* contra `bank_movements`: ±$1 o ±1% (configurable).

---

## 3) Vistas canónicas que necesita la UI
### 3.1 `v_facturas_compra` (reemplazar proxy a PO por AP real)
```sql
DROP VIEW IF EXISTS v_facturas_compra;
CREATE VIEW v_facturas_compra AS
SELECT
  ai.invoice_number     AS documento_numero,
  ai.invoice_date       AS fecha,
  ai.vendor_rut         AS proveedor_rut,
  ai.vendor_name        AS proveedor_nombre,
  ai.total_amount       AS monto_total,
  COALESCE(ai.currency,'CLP') AS moneda,
  COALESCE(ai.status,'open')  AS estado,
  COALESCE(ai.source_platform,'unknown') AS fuente
FROM ap_invoices ai;
```

### 3.2 `v_cartola_bancaria` (con estado de conciliación)
```sql
DROP VIEW IF EXISTS v_cartola_bancaria;
CREATE VIEW v_cartola_bancaria AS
SELECT
  bm.id,
  bm.fecha,
  bm.bank_name      AS banco,
  bm.account_number AS cuenta,
  bm.glosa,
  bm.monto,
  bm.moneda,
  bm.tipo,
  bm.saldo,
  bm.referencia,
  COALESCE(bm.fuente,'unknown') AS fuente,
  CASE WHEN rl.id IS NULL THEN 0 ELSE 1 END AS conciliado,
  COUNT(rl.id)           AS n_docs,
  SUM(rl.amount)         AS monto_conciliado
FROM bank_movements bm
LEFT JOIN recon_links rl ON rl.bank_movement_id = bm.id
GROUP BY bm.id;
```

### 3.3 `v_ap_reconciliation_flags` (excepciones 3‑way + conciliación)
> Si ya generaste 3‑way para PO↔GRN↔Factura, agrega un resumen por proyecto/OC/factura con flags `invoice_over_po`, `invoice_over_receipt` y `unreconciled_payment` (pago sin documento).

---

## 4) Endpoints 5555 a ajustar
- `/api/conciliacion/sugerencias` → ahora incluir **purchase** desde `v_facturas_compra` (AP real).
- `/api/conciliacion/confirmar` → **escribir en `recon_*`** (si vienen de Chipax ya conciliados, marcarlos como confirmados con `confidence=1.0` y `source='chipax_import'`).
- **Nuevo** `/api/reconciliaciones/sync_chipax` (opcional): dispara el importador y devuelve métricas (filas insertadas, *links* creados, filas no matcheadas).

---

## 5) QA / Verificación (consultas prácticas)
```sql
-- ¿Cuántas facturas AP importadas?
SELECT COUNT(*) FROM ap_invoices;

-- ¿Cuántos movimientos bancarios quedan sin conciliar?
SELECT COUNT(*) FROM v_cartola_bancaria WHERE conciliado=0;

-- ¿Cuántos links creados desde Chipax?
SELECT COUNT(*) FROM recon_links;

-- ¿Existen facturas con pago conciliado pero sin OC asociada? (para compras de servicio/misceláneo)
SELECT ai.invoice_number, ai.vendor_name, SUM(rl.amount) AS pagado
FROM ap_invoices ai
JOIN recon_links rl ON rl.ap_invoice_id = ai.id
GROUP BY ai.id
HAVING SUM(rl.amount) < ai.total_amount;
```

---

## 6) Plan de implementación (Copilot, paso a paso)
1) **DDL**: crear tablas `ap_invoices`, `ap_invoice_lines`, `recon_*` y `chipax_raw_*` (arriba).
2) **Importador** `tools/import_chipax_conciliacion.py`:
   - Lee todos los CSV de `data/raw/chipax/` por patrón.
   - Inserta el *raw* en `chipax_raw_*` y el canónico en `ap_invoices`/`sales_invoices`/`expenses`.
   - Resuelve `bank_movement_id` y crea `recon_reconciliations` + `recon_links` (soporta **split** N↔M).
3) **Reescribir** `v_facturas_compra` para usar `ap_invoices`.
4) **Actualizar** `v_cartola_bancaria` para traer `conciliado`, `n_docs`, `monto_conciliado`.
5) **Conciliación UI**: en las vistas (Factura, Cartola) mostrar **badge** `Conciliado` cuando `conciliado=1` o `invoice.paid>=x%`.
6) **Control Financiero 360**: usar `ap_pagado` desde `recon_links` + `sales_cobrado` idem, y reflejar de inmediato los saldos en el tablero.
7) **Jobs** (opcional): `scripts/sync_chipax.sh` que corre importador y refresca vistas.

---

## 7) Notas y decisiones de diseño
- **No sobre‑escribir** movimientos ni facturas existentes: *upsert* por `(vendor_rut, invoice_number, invoice_date, total_amount)`.
- **Proyectos**: si los CSV de Chipax no traen proyecto, usar `projects_analytic_map` y `project_aliases` (ya existe) para inferir `project_name` por proveedor/folio/glosa.
- **Explicabilidad**: guardar `recon_reconciliations.notes='chipax_import'` y **reasons** en un JSON opcional si decides extender el esquema.
- **Reapertura**: si luego Ofitec concilia distinto, crear nueva cabecera `reconciliation_id` y mantener historia (no borrar enlaces de importación, marcarlos con `notes='superseded'`).

---

## 8) Instrucciones concretas para Copilot
- Crea `tools/import_chipax_conciliacion.py` con funciones:
  - `load_csv(path) -> List[dict]` (usar `etl_common.py`).
  - `upsert_ap_invoice(row)` – mapea columnas Chipax.
  - `find_bank_movement(row) -> id?` – *match* tolerante por fecha/monto/glosa.
  - `create_reconciliation(ap_invoice_id, bank_movement_ids, amounts, meta)`.
- Añade migración SQL a `tools/create_finance_views.py` para recrear `v_facturas_compra` y `v_cartola_bancaria` como arriba.
- Actualiza `tools/reconcile_utils.py` para que **purchase** lea de `v_facturas_compra` (AP real) y no de PO.
- Endpoint `POST /api/reconciliaciones/sync_chipax` que llame al importador y devuelva métricas.
- Agrega tests:  
  1) AP conciliada 100% → `v_cartola_bancaria.conciliado=1` y `monto_conciliado=total`.  
  2) AP con split en 2 movimientos.  
  3) Movimiento bancario con 2 facturas (merge).  
  4) Regresión: `v_facturas_compra` ya **no** trae PO.

---

## 9) Qué gana el usuario inmediatamente
- Verá **ya conciliado** todo lo que Chipax traía (pagos/cobros históricos), sin trabajo manual.
- Los KPIs de **Control Financiero 360** pasan a “modo real”: *Pagado/Cobrado* provienen de conciliaciones efectivas.
- La **Conciliación Inteligente** de Ofitec parte desde un baseline confiable (histórico) y puede aprender de él.

---

### Cierre
Los datos **están** en tu repositorio (CSV de Chipax), pero la BD no los está **usando**. Con este plan, activamos AP/AR **reales** y sus **conciliaciones** en la capa canónica, alineado con *docs_oficiales* y preparando el terreno para 3‑way y cashflow sin fricción. ¡Dime si quieres que también deje un **seed** mínimo para demo (1 AP, 1 split, 1 AR) y los cURL para probar! 

