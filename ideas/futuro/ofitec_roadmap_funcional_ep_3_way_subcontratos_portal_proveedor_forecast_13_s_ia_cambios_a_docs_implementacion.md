# OFITEC — Roadmap Funcional (EP, 3‑Way, Subcontratos, Portal Proveedor, Forecast 13s, IA) + Cambios a *docs_oficiales* + Implementación
> Este documento consolida **mejoras clave** que faltan o conviene elevar en Ofitec.
> Está orientado a **Copilot**, con cambios precisos a *docs_oficiales*, contratos de datos (vistas `v_*`), endpoints 5555, UI/UX y QA. Mantiene compatibilidad con lo ya creado (CEO Dashboard, Landings Proyectos/Finanzas, Conciliación, Control Financiero). **Sin emojis**.

---

## 0) Objetivos
1) **Cerrar circuito** de obra: Presupuesto (PC) → OC → Recepción (GRN) → Factura → Pago; EP → FV → Cobro.  
2) **Trazabilidad auditable**: data lineage, bitácoras, fuentes.
3) **IA explicable**: auto‑match, anomalías, forecast caja, RAG sobre Drive.
4) **UX operativa**: dashboards con acciones, portal proveedor, inbox de tareas.

---

## 1) Estados de Pago (EP) end‑to‑end
### 1.1 Cambios a *docs_oficiales*
- **DB_CANONICA_Y_VISTAS.md**: agregar tablas y vistas EP: `ep_headers`, `ep_items`, `ep_versions`, `ep_approvals`, `v_ep_resumen`, `v_ep_to_invoice`.  
- **LEY_DE_PUERTOS_OFICIAL.md**: nuevos endpoints `/api/ep/*`, reglas de autorización (maker/checker).  
- **MAPEO_BASE_DATOS_PAGINAS.md**: rutas en UI: `/finanzas/ar/ep` (listado + detalle + aprobar).  
- **ESTRATEGIA_VISUAL.md**: patrón de revisión/aprobación, chips de estado, sin emojis.

### 1.2 Esquema (SQLite/PG)
```sql
CREATE TABLE ep_headers (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL,
  customer_id INTEGER NOT NULL,
  ep_number TEXT,            -- número interno del EP
  period_start DATE,
  period_end DATE,
  status TEXT CHECK(status IN ('borrador','en_revision','aprobado','rechazado')) DEFAULT 'borrador',
  total_bruto REAL DEFAULT 0,
  retenciones REAL DEFAULT 0,
  anticipos_aplicados REAL DEFAULT 0,
  total_neto REAL DEFAULT 0,
  created_at TEXT, created_by TEXT
);

CREATE TABLE ep_items (
  id INTEGER PRIMARY KEY,
  ep_id INTEGER NOT NULL REFERENCES ep_headers(id),
  wbs_code TEXT,            -- Cap/Partida/APU si aplica
  descripcion TEXT,
  unidad TEXT, cantidad REAL, precio REAL,
  avance_pct REAL DEFAULT 0, -- avance del periodo
  monto REAL DEFAULT 0
);

CREATE TABLE ep_versions (
  id INTEGER PRIMARY KEY,
  ep_id INTEGER NOT NULL REFERENCES ep_headers(id),
  version INTEGER NOT NULL, payload_json TEXT, created_at TEXT, created_by TEXT
);

CREATE TABLE ep_approvals (
  id INTEGER PRIMARY KEY,
  ep_id INTEGER NOT NULL REFERENCES ep_headers(id),
  approver TEXT, decision TEXT, note TEXT, decided_at TEXT
);
```

**Vistas**
```sql
CREATE VIEW v_ep_resumen AS
SELECT e.id, e.project_id, e.customer_id, e.status,
       e.total_bruto, e.retenciones, e.anticipos_aplicados, e.total_neto,
       (SELECT COALESCE(SUM(monto),0) FROM ep_items i WHERE i.ep_id=e.id) AS items_total
FROM ep_headers e;

CREATE VIEW v_ep_to_invoice AS
SELECT e.id AS ep_id, e.project_id, e.customer_id, e.total_neto
FROM ep_headers e WHERE e.status='aprobado'
AND NOT EXISTS (SELECT 1 FROM sales_invoices si WHERE si.ref_ep_id=e.id);
```

### 1.3 Endpoints 5555 (extracto)
```python
# /api/ep
GET /api/ep                # listar EP (filtros: proyecto, cliente, estado, periodo)
POST /api/ep               # crear EP
GET /api/ep/{id}           # detalle (con items y versiones)
PUT /api/ep/{id}           # editar (genera nueva version)
POST /api/ep/{id}/submit   # enviar a revisión
POST /api/ep/{id}/approve  # aprobar (maker/checker)
POST /api/ep/{id}/reject   # rechazar
POST /api/ep/{id}/to-fv    # generar FV desde EP aprobado
```

### 1.4 UI
- **/finanzas/ar/ep**: listado con filtros y chips; detalle con tabs: Resumen, Ítems, Aprobaciones, Historial; botón **Generar factura** en EP aprobado.  
- Importador EP (XLSX/CSV) con plantillas y mapeo asistido.

### 1.5 QA
- No se puede generar FV si EP≠aprobado.  
- `total_neto = total_bruto − retenciones − anticipos_aplicados`.  
- Bitácora de versiones y aprobaciones intacta.

---

## 2) Recepciones (GRN) y 3‑way match real
### 2.1 Cambios a *docs_oficiales*
- **DB_CANONICA_Y_VISTAS.md**: `goods_receipts`, `grn_items`, `v_po_funnel` y `v_3way_status_po_line_ext`.  
- **LEY_DE_PUERTOS_OFICIAL.md**: `/api/grn/*` y `/api/threeway/*`.  
- **MAPEO_BASE_DATOS_PAGINAS.md**: UI de Recepciones en Proyectos y Finanzas: `/proyectos/:id/recepciones` y `/finanzas/ap/ordenes` (vista financiera).

### 2.2 Esquema
```sql
CREATE TABLE goods_receipts (
  id INTEGER PRIMARY KEY,
  po_id INTEGER NOT NULL,
  supplier_id INTEGER NOT NULL,
  receipt_number TEXT,
  receipt_date TEXT,
  status TEXT CHECK(status IN ('borrador','confirmado')) DEFAULT 'confirmado',
  attachment_url TEXT,
  created_at TEXT, created_by TEXT
);

CREATE TABLE grn_items (
  id INTEGER PRIMARY KEY,
  grn_id INTEGER NOT NULL REFERENCES goods_receipts(id),
  po_line_id INTEGER NOT NULL,
  qty_received REAL DEFAULT 0,
  price_received REAL,
  note TEXT
);
```

**Vistas 3‑way**
```sql
-- Funnel: PO → GRN → AP → Pago
CREATE VIEW v_po_funnel AS
SELECT p.project_id, l.po_id,
       SUM(l.qty*l.price) AS po_monto,
       SUM(COALESCE(g.qty_received,0)*l.price) AS grn_monto,
       SUM(COALESCE(ai.amount,0)) AS ap_monto,
       SUM(COALESCE(pay.amount,0)) AS pagado
FROM po_lines l
LEFT JOIN (
  SELECT gi.po_line_id, SUM(qty_received) AS qty_received
  FROM grn_items gi GROUP BY gi.po_line_id
) g ON g.po_line_id=l.id
LEFT JOIN ap_invoice_lines ai ON ai.po_line_id=l.id
LEFT JOIN payments pay ON pay.po_line_id=l.id
JOIN purchase_orders p ON p.id=l.po_id
GROUP BY p.project_id, l.po_id;

-- Violaciones
CREATE VIEW v_3way_status_po_line_ext AS
SELECT l.id AS po_line_id,
       (l.qty*l.price) AS po_total,
       COALESCE(g.qty_received,0)*l.price AS grn_total,
       COALESCE(ai.total,0) AS ap_total,
       CASE WHEN COALESCE(ai.total,0) > (l.qty*l.price) THEN 1 ELSE 0 END AS invoice_over_po,
       CASE WHEN COALESCE(ai.total,0) > (COALESCE(g.qty_received,0)*l.price) THEN 1 ELSE 0 END AS invoice_over_receipt
FROM po_lines l
LEFT JOIN (
  SELECT po_line_id, SUM(qty_received) AS qty_received FROM grn_items GROUP BY po_line_id
) g ON g.po_line_id=l.id
LEFT JOIN (
  SELECT po_line_id, SUM(amount) AS total FROM ap_invoice_lines GROUP BY po_line_id
) ai ON ai.po_line_id=l.id;
```

### 2.3 Endpoints
```python
# Recepciones
GET /api/grn                 # listar por proyecto/proveedor/fecha
POST /api/grn                # crear GRN
GET /api/grn/{id}
POST /api/grn/{id}/attach    # subir evidencia

# 3-way
GET /api/threeway/violations?project_id=...   # usa v_3way_status_po_line_ext
```

### 2.4 UI
- Botón **“Recepcionar”** en OC/ítem; soporte parcial, devoluciones, tolerancias.  
- Panel de **3‑way** con filtros y acciones: solicitar recepción, bloquear aprobación de factura.

### 2.5 QA
- No permitir aprobar AP > PO o > GRN (según política).  
- Historial de recepciones con adjuntos.

---

## 3) Subcontratos con avances, anticipos y retenciones
### 3.1 Cambios a *docs_oficiales*
- **DB_CANONICA_Y_VISTAS.md**: `subcontracts`, `subcontract_items`, `subcontract_advances`, `subcontract_retentions`, `v_subcontract_status`.  
- **MAPEO_BASE_DATOS_PAGINAS.md**: `/proyectos/:id/subcontratos` + vista financiera en `/finanzas/ap/ordenes`.

### 3.2 Esquema
```sql
CREATE TABLE subcontracts (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL,
  supplier_id INTEGER NOT NULL,
  contract_number TEXT,
  currency TEXT, reajuste_uf INTEGER DEFAULT 0,
  start_date TEXT, end_date TEXT,
  amount REAL,
  retention_pct REAL DEFAULT 0,
  advance_amount REAL DEFAULT 0,
  status TEXT CHECK(status IN ('vigente','suspendido','terminado')) DEFAULT 'vigente'
);

CREATE TABLE subcontract_items (
  id INTEGER PRIMARY KEY,
  subcontract_id INTEGER NOT NULL REFERENCES subcontracts(id),
  wbs_code TEXT, descripcion TEXT, unidad TEXT,
  cantidad REAL, precio REAL,
  avance_acumulado REAL DEFAULT 0
);

CREATE TABLE subcontract_advances (
  id INTEGER PRIMARY KEY,
  subcontract_id INTEGER NOT NULL,
  amount REAL, applied REAL DEFAULT 0, created_at TEXT
);

CREATE TABLE subcontract_retentions (
  id INTEGER PRIMARY KEY,
  subcontract_id INTEGER NOT NULL,
  retained REAL DEFAULT 0, released REAL DEFAULT 0, guarantee_doc TEXT
);
```

**Vista**
```sql
CREATE VIEW v_subcontract_status AS
SELECT s.id, s.project_id, s.supplier_id,
       s.amount,
       (SELECT COALESCE(SUM(cantidad*precio*avance_acumulado),0) FROM subcontract_items si WHERE si.subcontract_id=s.id) AS avance_valorizado,
       (SELECT COALESCE(SUM(amount),0) FROM subcontract_advances a WHERE a.subcontract_id=s.id) AS anticipos,
       (SELECT COALESCE(SUM(retained-released),0) FROM subcontract_retentions r WHERE r.subcontract_id=s.id) AS retenciones_por_liberar
FROM subcontracts s;
```

### 3.3 Endpoints y UI
- `/api/subcontracts/*` CRUD; vínculo con OC/EP.  
- UI en proyecto: ficha con hitos/APU, avances, retenciones y anticipos; **acciones**: certificar avance, emitir factura del subcontratista, liberar retención.

### 3.4 QA
- No permitir que **facturación certificada** supere avance valorizado − retenciones + anticipos a amortizar.

---

## 4) Portal de pagos a proveedores (visibilidad “cuándo cobro”)
### 4.1 Cambios a *docs_oficiales*
- **LEY_DE_PUERTOS_OFICIAL.md**: `/api/portal/proveedores/*` (scope restringido a su RUT).  
- **ESTRATEGIA_VISUAL.md**: lineamientos del portal público (tema claro, accesibilidad).

### 4.2 Modelos/vistas
- `v_vendor_statement`: por proveedor → PO, GRN, Facturas, estados de pago, fecha estimada de pago (desde calendario de tesorería).  
- `portal_tokens`: tokens temporales para acceso seguro por link.

### 4.3 Endpoints (extracto)
```python
GET /api/portal/proveedores/statement?token=...
GET /api/portal/proveedores/invoices?token=...
```

### 4.4 UI (externo)
- Página simple con estado de documentos y **fecha estimada de pago**; opción de subir aclaraciones/adjuntos.

### 4.5 QA
- El proveedor solo ve su data; token expira; auditoría de accesos.

---

## 5) Flujo de caja 13 semanas (operativo)
### 5.1 Cambios a *docs_oficiales*
- **DB_CANONICA_Y_VISTAS.md**: `v_cash_forecast_13w` (semanal) y `v_ap_schedule`, `v_ar_expected`.  
- **MAPEO_BASE_DATOS_PAGINAS.md**: `/finanzas/tesoreria/pagos-programados` y calendario de caja.  
- **LEY_DE_PUERTOS_OFICIAL.md**: `/api/finance/treasury/forecast`.

### 5.2 Vistas
```sql
CREATE VIEW v_ar_expected AS
SELECT invoice_id, customer_id, project_id, due_date AS week, amount
FROM sales_invoices WHERE status IN ('emitida','enviada');

CREATE VIEW v_ap_schedule AS
SELECT invoice_id, supplier_id, project_id, due_date AS week, amount
FROM ap_invoices WHERE status IN ('recibida','aprobada');

CREATE VIEW v_cash_forecast_13w AS
SELECT week,
       SUM(CASE WHEN kind='in' THEN amount ELSE 0 END) AS cash_in,
       SUM(CASE WHEN kind='out' THEN amount ELSE 0 END) AS cash_out
FROM (
  SELECT week, amount, 'in' AS kind FROM v_ar_expected
  UNION ALL
  SELECT week, amount, 'out' FROM v_ap_schedule
  UNION ALL
  SELECT pay_date AS week, amount, 'out' FROM payroll_events
  UNION ALL
  SELECT tax_date AS week, amount, 'out' FROM tax_events
) t GROUP BY week ORDER BY week;
```

### 5.3 Endpoint
```python
GET /api/finance/treasury/forecast?weeks=13
```

### 5.4 UI
- Calendario 13 semanas con alertas de **brecha**; acciones: reprogramar pagos, priorizar cobranzas, enviar recordatorios.

### 5.5 QA
- El total semanal concuerda con `v_cash_forecast_13w`; cambios en pagos programados se reflejan inmediato.

---

## 6) Data lineage y calidad de datos
### 6.1 Cambios a *docs_oficiales*
- **DB_CANONICA_Y_VISTAS.md**: campos `source_system`, `source_doc`, `created_by/at`, `updated_by/at` en tablas clave; vista `v_data_quality`.
- **ESTRATEGIA_VISUAL.md**: mostrar “¿Por qué?” con fuente/vista.

### 6.2 Implementación
- Añadir columnas a `purchase_orders`, `ap_invoices`, `sales_invoices`, `goods_receipts`, `bank_movements`.  
- `v_data_quality` detecta faltantes críticos (proyectos sin PC, facturas sin proyecto, OC sin recepción, etc.).

### 6.3 UI
- Panel **Calidad de Datos** con lista priorizada y CTA a resolver.

---

## 7) IA explicable (auto‑match, anomalías, forecast, RAG)
### 7.1 Cambios a *docs_oficiales*
- **LEY_DE_PUERTOS_OFICIAL.md**: endpoints `/api/ml/*` (sólo lectura; acciones siguen en endpoints “clásicos”).  
- **ESTRATEGIA_CREACION_PAGINAS.md**: patrón de “sugerencias explicables” (mostrar evidencia y probabilidad).  

### 7.2 Endpoints (extracto)
```python
# Sugerencias
GET /api/ml/suggest/ap-match?invoice_id=...
GET /api/ml/suggest/ar-project?invoice_id=...
GET /api/ml/anomaly/po-line?po_line_id=...
GET /api/ml/forecast/cash?weeks=13
```

### 7.3 Evidencias mínimas por sugerencia
- Campos: `rule_hits` (monto, fecha, proveedor), `text_similarity`, `historical_pattern`, `confidence`.

### 7.4 UI
- Drawer de sugerencias: lista ordenada por confianza; botón **Aceptar** crea el vínculo (PO↔AP, FV↔Proyecto). Mostrar **por qué** (evidencias).

### 7.5 QA
- Toda sugerencia debe poder explicarse; registro en `recon_links` o tabla específica una vez aceptada.

---

## 8) Integraciones (SII, Bancos, Rindegastos, WhatsApp/email)
- **SII**: inbox DTE (futuro), mapeo proyecto por RUT/razón social/alias; referencias NC/ND.  
- **Bancos**: OFX/CSV multi‑banco con normalización; reglas por banco.  
- **Rindegastos**: import API → `expenses` con proyecto/centro de costo.  
- **WhatsApp/email**: aprobaciones y avisos con enlaces firmados.

*Docs*: **LEY_DE_PUERTOS_OFICIAL.md** y **MAPEO_BASE_DATOS_PAGINAS.md** deben documentar los puertos/handlers y rutas nuevas.

---

## 9) Gobierno, seguridad, operación
- **RBAC + SoD**: maker/checker en pagos; límites por monto/rol.  
- **Backups y seeds**: dataset demo consistente (PC, OC, GRN, AP, EP, FV, movimientos).  
- **Observabilidad**: logs estructurados, trazas; SLA API <250 ms para landings cacheadas.

---

## 10) UX operativa
- **Inbox por rol**: tareas de hoy (aprobar, conciliar, asignar, emitir FV).  
- **Search global** (Cmd/Ctrl+K): proyectos/OC/FV/EP/proveedor.  
- **No‑blank**: plantillas y ejemplos al abrir por primera vez.

---

## 11) Plan de implementación (por etapas)
### 11.1 Quick wins (2 semanas)
- `v_portfolio_health`, `v_kpi_conciliacion`, UI *Overview* Proyectos/Finanzas (ya definidos).  
- Auto‑match OC↔Factura (reglas + similitud) con explicación.  
- Recepciones básicas + vista `v_po_funnel` y `v_3way_status_po_line_ext`.  
- Alias de proyectos en importadores.  
- Panel **Calidad de Datos**.

### 11.2 30–60 días
- **EP completo** (versionado, aprobaciones, generar FV).  
- **Subcontratos** (contrato, avances, retenciones/anticipos).  
- **Pagos programados** y **cobranzas** operativas.

### 11.3 90 días
- **Forecast 13 semanas** con escenarios y dunning automatizado.  
- **Anomalías** y **RAG** para explicaciones.  
- **Portal proveedor** (lite) con fecha comprometedora de pago.

---

## 12) Criterios de aceptación (globales)
1) Todo KPI o alerta muestra **fuente/vista `v_*`** al pedir “¿Por qué?”.  
2) 3‑way bloquea AP > PO o > GRN según política.  
3) EP → FV requiere EP `aprobado` y queda traza.  
4) Forecast 13s concilia con calendario de pagos/cobros.  
5) Sin emojis; accesibilidad AA; navegación por teclado.  
6) Logs/auditoría presentes para aprobaciones, conciliaciones y generadores (EP→FV).

---

### Cierre
Este roadmap completa Ofitec como **ERP de proyectos** listo para operación y auditoría: EP y subcontratos como primera clase, recepciones con 3‑way real, portal de proveedor, forecast de caja operativo y **IA explicable**. Todo trazable a vistas canónicas y **en línea con *docs_oficiales***, con cambios explícitos y progresivos para no romper lo ya construido.

