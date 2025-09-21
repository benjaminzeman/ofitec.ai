# OFITEC — Revisión y rediseño de **Conciliación Bancaria**
> Auditoría técnica de la implementación actual en `ofitec.ai` + plan de mejoras centrado en **usabilidad** y en un **motor inteligente** explicable, con aprendizaje continuo. Todo alineado a *docs_oficiales* (Ley de Puertos/UI 3001–API 5555/DB canónica).

---

## 0) Qué hay hoy (radiografía rápida)
**Backend 5555 (Flask)**
- `GET /api/finanzas/cartola_bancaria` lee la **vista canónica** `v_cartola_bancaria` con filtros básicos (rut, moneda, estado, rango de fechas, search) usando `_query_view(...)`.
- `POST /api/conciliacion/sugerencias` arma un **Source** (bank/sales/purchase/expense/payroll/tax) y delega a `tools/reconcile_utils.suggest_matches(...)` para generar **sugerencias**.
  - **Scoring actual (reglas)**: match por **monto** (exacto/tolerancia), **fecha** (exacta/ventana) y **referencia** (fuzzy hit). → Simple y útil, pero limitado.
- `POST /api/conciliacion/confirmar` sólo **proxy** a un servicio externo (`CONCILIACION_SERVICE_URL`). Si no está la URL, responde *no‑op* 202.

**Servicio opcional (monorepo)** `services/conciliacion_bancaria/*`
- `core/intelligent_matching.py`: **motor avanzado** (resolución de identidades por **RUT/aliases**, similitud de texto, patrones de **folio**, soporte **1↔N / N↔1** *subset‑sum*, razones explicables).
- `core/ml_engine.py`: esqueleto de **ML** (features numéricas y de texto; meta *precision@1 ≥ 0.92, recall@5 ≥ 0.98*).
- `database/schema.py` + `web/index.html`: base de datos y UI standalone (no está cableado al 5555).

**Frontend (plantillas HTML + JS unificado)**
- Página dedicada: `templates/pages/conciliacion_bancaria.html`.
- Otras vistas (Facturas, Proveedores, Cartola) **no** muestran aún botón “Conciliar” contextual.

**Importadores/ETL**
- `tools/import_bank_movements.py` (CSV→`bank_movements`).
- `tools/create_finance_views.py` crea placeholders (incl. `v_cartola_bancaria` si no existe).

**Conclusión rápida**: hay **tres niveles** co‑existiendo: (1) UI página única, (2) sugerencias **reglas simples** en 5555 y (3) **motor avanzado**/ML en carpeta `services`, **sin integrar**. Perfecto para iterar: ya tenemos la materia prima; falta **unir** todo, mejorar **UX** y cerrar **circuito de aprendizaje**.

---

## 1) Brechas principales (qué mejorar ya)
1) **UX contextual**: falta el botón *Conciliar* en **todas** las vistas relevantes (Factura Venta/Compra, Cartola, Pagos, Gastos).
2) **Cadena de valor incompleta**: el `confirmar` no impacta la **DB canónica** (no asienta relación ni cambia estados).
3) **Capacidades de matching**: reglas actuales no cubren **splits** (1↔N), **multimoneda**, **comisiones**/redondeos, **alias** por proveedor, ni **señales fuertes** (RUT/IBAN/folio).
4) **Explicabilidad/Confianza**: las sugerencias no muestran **razones** ni `confidence`, ni aprenden de las decisiones del usuario.
5) **Rendimiento**: faltan **índices** e **inverted index** de texto para buscar rápido candidatos en cartola.
6) **Gobernanza y auditoría**: no hay bitácora canónica de reconciliaciones (quién concilió, qué, cuándo, por qué).

---

## 2) Rediseño propuesto (arquitectura funcional)
### 2.1 Flujo UX unificado (in‑context)
- **Desde una Factura** (venta/compra): botón **Conciliar** → *drawer* lateral con **Top‑5** movimientos sugeridos + razones (🧠). Atajos: `Enter` **aceptar 1#** si `confidence ≥ 0.92`; `S` **Split**; `R` **Regla**.
- **Desde una línea de Cartola**: botón **Conciliar** → sugiere **documentos** (facturas, gastos, nómina, impuestos). Soporta **agrupar** varios documentos hasta cuadrar.
- **Desde “Pagos”**: igual que cartola pero filtrando por **proveedor/cliente** y fechas.

> **Principio**: *el usuario no piensa en dónde conciliar; concilia desde donde está.*

### 2.2 Motor de sugerencias (capa 5555)
- Reemplazar `reconcile_utils` por un **adapter** que use el motor avanzado:
  - `POST /api/conciliacion/sugerencias`: llama a `intelligent_matching.suggest(...)` (features + reglas), devuelve `{items:[{candidate, confidence, reasons[]}...]}`.
  - **Features**:
    - **Montos**: delta absoluto/%; tolerancias por **moneda** y por **tipo** (p.ej., *impuestos* permiten redondeos).
    - **Fechas**: distancia días; ventana configurable por **tipo** (venta: +5/‑2; compra: +10/‑3; nómina/impuestos: fijos).
    - **Identidad**: match por **RUT**, **alias** aprendidos, **IBAN/cta** (si la cartola trae CV), **folio** extraído por regex.
    - **Texto**: similitud tokens (cosine/Jaccard simple) + *whitelist* de patrones CL específicos (TESORERÍA, PREVIRED, SII, PAT, COMISIÓN).
  - **Explicabilidad**: cada sugerencia trae `reasons` (ej.: `monto=exact`, `fecha=+2d`, `folio=123456`, `RUT=76.543.210‑K`, `alias=ACME (conf 86%)`).

### 2.3 Confirmación y asientos
- `POST /api/conciliacion/preview` → simula asiento(s) **sin commitear**.
- `POST /api/conciliacion/confirmar` → escribe en tablas **canónicas**:
  - `reconciliations` (cabecera) y `reconciliation_links` (N↔M: movement_id ↔ {invoice_id|expense_id|payroll_id|tax_id}).
  - Cambia estados: `invoice.balance_due`, `bank_movements.state='conciliado'`.
  - **Bitácora**: `audit_reconciliation` con `user_id`, `confidence`, `reasons` y `hash` anti‑tamper.

### 2.4 Aprendizaje continuo (sin MLOps complejo)
- `training_events` guarda **positivos** (aceptados) y **negativos** (rechazados/cambiados).
- Actualizar **tabla `recon_aliases`**: (rut, razón social, variantes, regex) con **contador** y **confianza**.
- **Auto‑reglas** (user‑level): *si proveedor X + monto ~ Y ± 1% + patrón “arrend” → default a cuenta 5130; vencimiento en 30d.*
- **Auto‑conciliación segura** (opcional): si `confidence ≥ 0.97` y tipo ∈ {boleta bancaria, intereses/bank fee, mantención} → concilia **silenciosamente** y deja notificación.

---

## 3) Modelo de datos (SQLite/Postgres)
> Nuevas tablas (prefijo `recon_`), todas con FK y `created_at/updated_at`.

```sql
-- Reconciliaciones (cabecera)
CREATE TABLE recon_reconciliations (
  id INTEGER PRIMARY KEY,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  context TEXT CHECK(context IN ('bank','sales','purchase','expense','payroll','tax')) NOT NULL,
  confidence REAL,
  user_id TEXT,
  notes TEXT
);

-- Enlaces N↔M (permite split/group)
CREATE TABLE recon_links (
  id INTEGER PRIMARY KEY,
  reconciliation_id INTEGER NOT NULL REFERENCES recon_reconciliations(id) ON DELETE CASCADE,
  bank_movement_id INTEGER,            -- FK bank_movements
  sales_invoice_id INTEGER,            -- FK sales_invoices
  purchase_invoice_id INTEGER,         -- FK purchase_orders_unified (o facturas AP)
  expense_id INTEGER,
  payroll_id INTEGER,
  tax_id INTEGER,
  amount REAL NOT NULL                 -- por si el split no es 100% a un único doc
);

-- Eventos de entrenamiento (feedback humano)
CREATE TABLE recon_training_events (
  id INTEGER PRIMARY KEY,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  context TEXT,
  source_json TEXT NOT NULL,
  chosen_json TEXT NOT NULL,
  accepted INTEGER NOT NULL CHECK(accepted IN (0,1)),
  reasons TEXT
);

-- Aliases de contrapartes
CREATE TABLE recon_aliases (
  id INTEGER PRIMARY KEY,
  rut TEXT,
  razon_social TEXT,
  pattern TEXT,          -- regex o texto normalizado
  confidence REAL DEFAULT 0.5,
  hits INTEGER DEFAULT 0
);

CREATE INDEX idx_links_bank ON recon_links(bank_movement_id);
CREATE INDEX idx_links_sales ON recon_links(sales_invoice_id);
CREATE INDEX idx_links_purchase ON recon_links(purchase_invoice_id);
```

**Índices bancarios recomendados**
```sql
CREATE INDEX IF NOT EXISTS idx_bm_date ON bank_movements(fecha);
CREATE INDEX IF NOT EXISTS idx_bm_amount ON bank_movements(monto);
CREATE INDEX IF NOT EXISTS idx_bm_norm ON bank_movements(descripcion_norm);
```
> `descripcion_norm` = `UPPER(descripcion)` sin stopwords; crear columna calculada o vista materializada.

---

## 4) API (5555) — contratos claros
```yaml
POST /api/conciliacion/sugerencias
  body: { source_type: 'bank'|'sales'|'purchase'|'expense'|'payroll'|'tax', id?: number, amount?: number, date?: 'YYYY-MM-DD', ref?: string, currency?: 'CLP'|'USD'|..., days?: 5, amount_tol?: 0.01 }
  200: { items: [ { candidate: {type,id,doc,fecha,amount,currency}, confidence: 0.0..1.0, reasons: ["monto=exact","fecha=+2d","RUT=..."] } ] }

POST /api/conciliacion/preview
  body: { context: 'bank'|..., links: [{bank_movement_id, sales_invoice_id?, purchase_invoice_id?, ... , amount}] }
  200: { ok: true, simulated_entries: [...], deltas: {invoice_balance_after, movement_state_after} }

POST /api/conciliacion/confirmar
  body: { context, links: [...], metadata?: {notes, user_id}, confidence, reasons }
  200: { ok: true, reconciliation_id, changes: {...} }
```

---

## 5) UI (3001/plantillas) — componentes y patrones
- **Botón Conciliar** en: Facturas Venta/Compra, Cartola, Pagos, Gastos, Impuestos.
- **Drawer de conciliación** con:
  - **Top‑5** candidatos (lista compacta) + `confidence` + **razones**; acción **Aceptar** (`Enter`) o **Split** (`S`).
  - **Búsqueda** manual (por monto/fecha/texto) con atajos.
  - **Reglas**: botón “Crear regla desde esta selección”.
  - **Acciones masivas**: seleccionar varias líneas de cartola → sugerir **agrupaciones**.
- **Badges**: `conciliado`, `pendiente`, `en revisión`.
- **Timeline**: en detalle de factura mostrar **Factura → Conciliación → Pago**.

**Componentes (Copilot)**
- `ReconcileDrawer.tsx` (client): props `{context, sourceId}`; consume `/api/conciliacion/sugerencias`, `preview`, `confirmar`.
- `ConciliarButton.tsx`: icono persistente con atajo `Shift+C`.
- `ReasonChips.tsx`: chips *monto/fecha/RUT/folio/alias/text-sim*.

---

## 6) Motor Inteligente (cómo cerramos el círculo)
1) **Candidate Generation**: por **monto** (±tol), **fecha** (±ventana), **texto** (índice invertido), **identidad** (RUT/alias), **folio** detectado.
2) **Ranking**: puntajes por feature; calibrar a [0..1] con `sigmoid` sencilla.
3) **Thresholds**: `auto ≥ 0.97` (*silent*), `one‑click ≥ 0.92` (Enter), `needs‑review < 0.92`.
4) **Feedback**: cada confirmación/rechazo persiste en `recon_training_events` y ajusta `recon_aliases`/ponderaciones.
5) **Explain**: siempre **mostrar razones**. Nunca caja negra.

**Ejemplo de sugerencia**
```json
{
  "candidate": { "type": "sales", "id": 8812, "doc": "FV-003421", "fecha": "2025-09-10", "amount": 25369786, "currency": "CLP" },
  "confidence": 0.94,
  "reasons": ["monto=exact","fecha=+1d","folio=3421","RUT=76.543.210-K"]
}
```

---

## 7) Integración con **Proyecto 360°** / **Cashflow**
- Conciliación **de ventas** → **inflow** confirmado por proyecto/cliente.
- Conciliación **de compras**/gastos/nómina → **outflow** confirmado, con **match** a PO/GRN/Factura (3‑way) cuando aplique.
- Auditoría de **desvíos**: si pago>factura o factura>OC/recepción, **alerta**.
- **Reforecast** cashflow: al confirmar, mover monto del *expected* al *actual* y recalcular bucket mensual.

---

## 8) Seguridad, auditoría, pruebas
- **Maker–Checker** opcional para conciliaciones > umbral (monto o riesgo).
- **Bitácora** con `hash` (sha256) de los enlaces.
- **Pruebas**:
  - unit: *scoring*, *split*, *alias learning*;
  - integration: `/sugerencias`→`/preview`→`/confirmar`;
  - E2E: conciliar desde **Factura** y desde **Cartola**.

---

## 9) Plan por sprints (2–3 semanas)
**S1 — UX contextual + sugerencias avanzadas**
- Botón “Conciliar” en todas las vistas.
- Adapter 5555 → `intelligent_matching` + razones.
- Índices `bank_movements` y `descripcion_norm`.

**S2 — Confirmación, auditoría y aprendizaje**
- Tablas `recon_*`, endpoints `preview/confirmar`.
- Bitácora y *maker–checker*.
- `training_events` + actualización automática de `recon_aliases`.

**S3 — Auto‑conciliación segura + cashflow**
- Umbral `auto` + notificaciones.
- Hook de **cashflow** y panel de métricas: *precision@1*, *recall@5*, % auto.

---

## 10) Notas para Copilot (archivos y cambios concretos)
- **Backend** `backend/server.py`
  - Reemplazar uso de `tools/reconcile_utils` por adapter a `services/conciliacion_bancaria/core/intelligent_matching.py`.
  - Crear rutas `POST /api/conciliacion/preview` y ajustar `confirmar` a DB canónica (`recon_*`).
- **DB** `tools/create_finance_views.py`
  - Añadir columna `descripcion_norm` (o vista materializada) y crear índices `idx_bm_*`.
  - Generar migraciones para `recon_*` tablas.
- **Frontend** `backend/templates/...` + `/static/js`
  - Componente `ReconcileDrawer` y `ConciliarButton`; integrar en **Facturas**, **Cartola**, **Gastos**.
  - Mostrar `confidence` y `reasons` (chips) y acciones **Split**/**Regla**.
- **Service** `services/conciliacion_bancaria/`
  - Exponer función `suggest(source, options)` importable desde 5555.
  - Gumificar `ml_engine` (opcional) solo si tenemos suficientes `training_events`.

---

### Cierre
La base es **sólida**: ya tienes vista canónica, endpoints, y un motor avanzado de conciliación *in‑repo*. El salto ahora es **integrar** ese motor al 5555, llevar el botón **Conciliar** a **todas** las pantallas, y **aprender** de cada click. El resultado: menos fricción, menos errores, y un “cerebro” que de verdad trabaja por el usuario.

