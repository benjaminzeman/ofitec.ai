# OFITEC — Playbook Módulo **Proyecto** (Detalle 360º + IA + Drive/WhatsApp)

**Objetivo:** Que al hacer clic en un **Proyecto** se despliegue una vista 360º (finanzas, compras, ventas, tiempo, documentos, comunicaciones) con **IA operativa** y conectores **Google Drive** y **WhatsApp**, todo coherente con tus reglas (Ley de Puertos 3001/5555, DB Canónica/Vistas, Estrategia Visual).

---

## 1) Principios y alcances

- **Proyecto-centrismo:** todo cuelga del `project_id`/`project_name` (alias normalizado).
- **Canales oficiales:** UI en **3001**, API JSON en **5555**.
- **DB Canónica:** sólo vistas/tablas autorizadas; nada crudo en prod.
- **Experiencia:** contenido **útil en 10 segundos** + drill-down; semáforos y explicación.
- **IA con propósito:** *copiloto de proyecto* (resumen, Q&A, alertas, acciones guiadas).

---

## 2) Diseño de la página “Proyecto”

### 2.1 Layout (above the fold)

- **Header**: Nombre, estado (Activo/En cierre), fechas (inicio/fin), Jefe de Proyecto, carpeta Drive (link), botón WhatsApp (lista de hilos).
- **KPIs (fila superior)**:
  - **Ventas contratadas** (AR firmadas)
  - **Presupuesto de Costo (PC)**
  - **Comprometido (OC)**
  - **Gastado / Facturado (AP)**
  - **Pagado**
  - **Margen esperado** (Ventas − PC)
  - **Margen comprometido** (Ventas − OC)
  - **Margen real** (Ventas − AP)
  - **Cashflow neto (mes)** (Inflows − Outflows)
  - **% Avance físico** (si existe fuente)
- **Barras/Gráfico**: Waterfall PC → OC → AP → Pagado; línea Ventas (techo).
- **Semáforos**: Budget overrun, Factura>OC, Pago>Factura, proveedores críticos, atraso en certificaciones.

### 2.2 Secciones/Tabs

1. **Resumen** (KPI, gráfico, flags, próximos hitos).
2. **Compras** (OC, releases, change orders, recepciones).
3. **Finanzas** (AP, pagos, AR, cobranzas, cashflow).
4. **Presupuesto** (capítulos/partidas, desvíos).
5. **Tiempo** (cronograma, milestones; si hay tareas/avances).
6. **Documentos** (Google Drive: planos, contratos, certificados).
7. **Conversaciones** (WhatsApp: hilos por proveedor/tema).
8. **IA / Copiloto** (resumen, Q&A, checklist semanal, explicaciones, acciones).

---

## 3) Vistas y fuentes de datos

> Si alguna no existe, crear la **vista canónica** equivalente (SQLite/Postgres). Mantener `project_name` normalizado y `project_aliases`.

- **Presupuesto**: `v_presupuesto_totales` (PC total), `partidas`, `capitulos`.
- **Compras/OC**: `purchase_orders_unified`, `po_line_allocations` (para imputación por partida).
- **Facturas (AP)**: `v_facturas_compra` (con `project_name`/`po_line_id`).
- **Pagos**: `v_cartola_bancaria` (mapeada a facturas/proyecto).
- **Ventas/AR**: `v_ventas_contratadas` (contratos/ventas) y `v_cobranzas` (cobros) — crear si no existe.
- **Cashflow**: `v_cashflow_expected`, `v_cashflow_actual`, `v_cashflow_variance`.
- **Tiempo**: `v_project_schedule` (si hay), `v_progress` (certificados/avance).
- **Docs**: `project_drive_files` (metadatos de Drive).
- **WhatsApp**: `whatsapp_threads`, `whatsapp_messages` (metadatos + link a media).

### 3.1 Vista consolidada `v_project_summary`

**Campos**: `project_id, project_name, sales_contracted, pc_total, committed, invoiced_ap, paid, ar_invoiced, ar_collected, margin_expected, margin_committed, margin_real, cashflow_net_month, progress_pct`.

---

## 4) API (5555) — contratos de endpoints

- `GET /api/projects/:id/summary` → KPIs + flags + próximos hitos (7 días).
- `GET /api/projects/:id/purchases` → OC, releases, COs, recepciones (paginado, filtros).
- `GET /api/projects/:id/budget` → capítulos/partidas con comprometido y disponible.
- `GET /api/projects/:id/finance` → AP/AR/Payments/Collections + cashflow (expected/actual/variance).
- `GET /api/projects/:id/time` → cronograma + milestones + %avance.
- `GET /api/projects/:id/docs` → Drive (árbol y búsqueda).
- `GET /api/projects/:id/chats` → hilos WhatsApp por proveedor/tema.
- `POST /api/projects/:id/ai/summary` → resumen semanal (texto + bullets + riesgos).
- `POST /api/projects/:id/ai/qna` → Q&A con grounding en DB + Drive.
- `POST /api/projects/:id/ai/draft` → redacción (correo/whatsapp), con contexto de proyecto.

**Flags estándar**: `exceeds_budget`, `invoice_over_po`, `overpaid`, `no_delivery_plan`, `late_certificate`, `collection_risk`.

---

## 5) Frontend (3001) — componentes clave

- **KPICard** (tokens visuales: Inter, lime #84CC16, radius 12, sin sombras).
- **Waterfall/Progress** (Recharts).
- **Tabla árbol** (Capítulo→Partida) con chips de estado y `%OC/PC`, `%AP/PC`, `%Paid/AP`.
- **Timeline** (milestones) y **Cashflow buckets**.
- **Panel de Alertas** (explicables, con CTA).
- **Panel IA (Copiloto)**: input + chips de intents (resumen, riesgo, explicar desvío, crear OC, pedir cotización).
- **Drive Browser** (listado, filtro por tipo, preview PDF/IMG).
- **WhatsApp Inbox** (hilos por proveedor/tema, búsqueda, link a PO/factura/documento).

---

## 6) IA aplicada al módulo Proyecto

### 6.1 Copiloto de Proyecto (RAG + acciones)

- **RAG** por proyecto: índice vectorial con **DB (vistas)** + **Drive** (texto de PDFs/Docs) + metadatos.
- **Q&A** con citas (links a filas/archivos).
- **Resúmenes semanales**: venta/compra/gasto/cashflow/avances/alertas.
- **Explicador de desvíos**: “¿Por qué aumentó OC/Partida 3.1?” → agrupa POs, cambios de precio, nuevos releases.
- **Acciones**: crear borrador de OC; preparar mensaje WhatsApp/correo a proveedor; generar checklist.

### 6.2 Alertas inteligentes

- **Anomalías**: factura fuera de rango, pago duplicado, precio anómalo vs histórico.
- **Riesgo de flujo**: expected\_outflow > expected\_inflow en mes N.
- **Ejecución**: OC sin delivery plan, certificados atrasados, colección AR vencida.

---

## 7) Google Drive — integración por proyecto

- **Carpeta raíz por proyecto** (ID en `projects`).
- **Sync de metadatos**: `file_id, title, mime, url, owners, modified_time, path`.
- **Ingesta**: OCR y extracción de texto (PDF/DOCX) → índice del proyecto.
- **Vinculación**: documentos marcados a **PO/Factura/Contrato/Partida**.
- **Búsqueda**: por texto, por entidad (PO, partida, proveedor), por fecha.
- **Permisos**: respetar sharing; nunca exponer fuera del proyecto.

---

## 8) WhatsApp — integración operativa

- **Hilos por proveedor/tema**; mensajes con `from, to, timestamp, text, media_url`.
- **Enlaces**: un hilo puede estar ligado a `po_id` o `invoice_id`.
- **Plantillas**: confirmación de entrega, solicitud de cotización, recordatorio de factura.
- **Consentimiento y auditoría**: log de envíos/recepciones; respeto de políticas.
- **IA**: clasificar intención, extraer fechas/PO/montos, proponer respuestas.

---

## 9) Cashflow — enfoque unificado (Proyecto)

- **Expected Outflows**: de `v_cashflow_expected` (materiales: delivery\_plan; servicios: certificados).
- **Expected Inflows**: de **Ventas/AR** (hitos o facturas cliente) + términos de cobro.
- **Actual**: de `v_cartola_bancaria` (pagos/cobros conciliados).
- **Variance**: vista de brecha por mes, con explicación (IA) y CTA (ajustar entregas/certificados/condiciones).

---

## 10) Seguridad y gobierno

- **Roles** por módulo (proyecto/ compras/ finanzas/ lectura).
- **Bitácora** de cambios (OC, contratos, certificados, forecast).
- **Políticas**: maker-checker por monto; bloqueo de reglas (Factura≤OC, Pago≤Factura).

---

## 11) Plan de implementación (2 sprints)

**Sprint 1**

- `GET /projects/:id/summary|purchases|budget|finance` (mínimos).
- UI Resumen + Compras + Presupuesto + Cashflow (expected con materiales).
- Copiloto: Q&A básico con DB + Drive.
- WhatsApp listado sólo lectura.

**Sprint 2**

- Ventas/AR + cobranzas, certificados de avance y forecast servicios.
- IA avanzada: explicador de desvíos, alertas automáticas, redacción de mensajes.
- Acciones: crear borrador de OC desde Copiloto.
- Inbox WhatsApp operativo (enviar/recibir con plantillas aprobadas).

---

## 12) Contratos de ejemplo (resúmenes JSON)

```json
// GET /api/projects/42/summary
{
  "project_id": 42,
  "project_name": "Edificio Ofitec Centro",
  "sales_contracted": 1750000000,
  "budget_cost": 1320000000,
  "committed": 980000000,
  "invoiced_ap": 720000000,
  "paid": 650000000,
  "ar_invoiced": 400000000,
  "ar_collected": 320000000,
  "margin_expected": 430000000,
  "margin_committed": 770000000,
  "margin_real": 1030000000,
  "cashflow_net_month": -75000000,
  "progress_pct": 41,
  "flags": ["exceeds_budget"],
  "next_milestones": [{"title":"Certificado Septiembre","date":"2025-09-30"}]
}
```

---

## 13) Notas para Copilot

- Mantener cohesión con **DB Canónica** y respetar **Ley de Puertos**.
- Si una vista/tabla no existe, **crear la vista** primero (no leer crudo).
- En UI, usar tokens: Inter, lime #84CC16, radius 12, **sin sombras**, bordes 1px, espacios generosos, KPICard/Progress/Badge/Table.
- Priorizar **explicabilidad**: cada alerta/flag debe ofrecer *por qué* y *qué hacer* (CTA).

