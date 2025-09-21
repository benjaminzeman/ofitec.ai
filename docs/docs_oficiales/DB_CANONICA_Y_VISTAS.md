# BASE DE DATOS CANÓNICA Y VISTAS – GUÍA MAESTRA

Este documento consolida el diseño de la Base de Datos canónica del Portal OFITEC y los contratos de todas las vistas por módulo. Es la guía de referencia para ingeniería de datos, backend y frontend. Complementa y expande: LEY_DE_BASE_DATOS_OFICIAL.md, LEY_DE_PUERTOS_OFICIAL.md y DB_SCHEMA_AND_OPS.md.

## Principios
- Canónico: una sola BD (SQLite en dev) y contratos estables (vistas).
- Idempotencia: ingestiones que no duplican y registran diferencias.
- Integridad: RUT normalizado con DV; fechas ISO-8601; monedas ISO 4217.
- Transversal: Conciliación bancaria vive como servicio externo; el Portal consume snapshots/vistas de solo lectura.

## Entidades nucleares (tablas)
- projects: id, zoho_project_id, name, client_id, status, budget_total, start_date, end_date, analytic_code, slug, created_at
- vendors_unified: id, rut_clean (UNIQUE), name_normalized, source_platform, zoho_vendor_name, created_at
- customers: id, rut_clean (UNIQUE), name_normalized, created_at
- purchase_orders_unified: id, vendor_rut, zoho_vendor_name, po_number, po_date, total_amount, currency, status, source_platform, zoho_po_id, zoho_project_id, zoho_project_name, exchange_rate, migration_id, created_at
- purchase_lines_unified: id, po_id, item_name, item_desc, quantity, unit_price, line_total, currency, tax_percent, tax_amount, uom, status, zoho_line_id, created_at
- sales_invoices: id, customer_rut, customer_name, invoice_number, invoice_date, total_amount, currency, status, source_platform, dte_id, project_id, created_at
- sales_invoice_lines: id, invoice_id, item_name, item_desc, quantity, unit_price, line_total, currency, tax_percent, tax_amount, uom, status
- expenses: id, fecha, categoria, descripcion, monto, moneda, proveedor_rut, proyecto, fuente, status, comprobante
- taxes: id, periodo, tipo, monto_debito, monto_credito, neto, estado, fecha_presentacion, fuente
- previred_contributions: id, periodo, rut_trabajador, nombre_trabajador, rut_empresa, monto_total, estado, fecha_pago, fuente
- payroll_slips: id, periodo, rut_trabajador, nombre_trabajador, cargo, bruto, liquido, descuentos, fecha_pago, fuente
- bank_accounts: id, bank_name, account_number, currency, holder, alias
- bank_movements: id, fecha, bank_name, account_number, glosa, monto, moneda, tipo, saldo, referencia, fuente, external_id
- cashflow_planned: id, project_id, category, fecha, monto, moneda, status, source_ref
- project_aliases: id, from_name, to_name (tabla auxiliar para unificar alias de nombres de proyecto entre fuentes; UNIQUE(from_name,to_name))
- zoho_po_raw (staging): id, source_file, row_index, row_json, import_batch_id, hash, created_at
- projects_analytic_map: id, zoho_project_id (UNIQUE), zoho_project_name, analytic_code, slug, created_at
- subcontracts: id, vendor_rut, project_id, contract_number, fecha, monto_total, moneda, status
- subcontract_progress: id, subcontract_id, periodo, avance_pct, monto_bruto, retenciones, monto_neto, fecha_emision, status
- daily_reports: id, project_id, fecha, actividades, cuadrilla_json, avance_pct, observaciones
- progress_photos: id, report_id, project_id, fecha, url, description, tags
- gps_locations: id, project_id, fecha_hora, lat, lon, device_id
- documents: id, project_id, title, doc_type, path, version, status, created_at
- doc_embeddings: id, document_id, chunk_index, embedding, text, created_at
- rfi_requests: id, project_id, numero, titulo, descripcion, solicitante, responsable, fecha_solicitud, estado
- rfi_responses: id, rfi_id, fecha_respuesta, respondido_por, contenido, adjuntos
- hse_incidents: id, project_id, fecha, tipo, gravedad, descripcion, estado, acciones
- hse_inspections: id, project_id, fecha, checklist, hallazgos, cumplimiento_pct, responsable
- epp_detections: id, project_id, fecha_hora, image_url, detecciones_json, cumplimiento_pct
- risk_matrix: id, project_id, riesgo, probabilidad, impacto, nivel, estado, owner, mitigaciones
- risk_predictions: id, project_id, categoria, score, detalle, fecha_modelo, version_modelo
- users, roles, permissions, user_roles, sessions (admin): ver Admin más abajo.

## Vistas canónicas (Finanzas)

- v_facturas_compra: documento_numero, fecha, proveedor_rut, proveedor_nombre, monto_total, moneda, estado, fuente
- v_facturas_venta: documento_numero, fecha, cliente_rut, cliente_nombre, monto_total, moneda, estado, fuente
- v_gastos: gasto_id, fecha, categoria, descripcion, monto, moneda, proveedor_rut, proyecto, fuente
- v_impuestos: periodo, tipo, monto_debito, monto_credito, neto, estado, fecha_presentacion, fuente
- v_previred: periodo, rut_trabajador, nombre_trabajador, rut_empresa, monto_total, estado, fecha_pago, fuente
- v_sueldos: periodo, rut_trabajador, nombre_trabajador, cargo, bruto, liquido, descuentos, fecha_pago, fuente
- v_cartola_bancaria: fecha, banco, cuenta, glosa, monto, moneda, tipo, saldo, referencia, fuente

## Vistas extendidas por módulo

### Finanzas/Tesorería

- v_proveedores_resumen: proveedor_rut, proveedor_nombre, total_ordenes, monto_total, ultima_orden
- v_proyectos_resumen: proyecto, project_id, total_ordenes, proveedores_unicos, monto_total, fecha_min, fecha_max
- v_tesoreria_saldos_consolidados: banco, cuenta, moneda, saldo_actual, movimientos_30d
- v_cashflow_semana: semana, categoria, monto, moneda, status
- v_ordenes_compra: oc_id, po_number, fecha, proveedor_rut, proveedor_nombre, monto_total, moneda, estado, proyecto, project_id, fuente
- v_ordenes_compra_lineas: oc_id, linea_id, item_name, item_desc, quantity, unit_price, line_total, currency, uom, estado
- v_control_financiero_resumen (opcional): project_name, presupuesto, comprometido, disponible_conservador

### Proyectos/Subcontratos

- v_proyectos_kpis: project_id, proyecto, presupuesto, compras, ventas, margen, avance, riesgo
- v_subcontratos_resumen: subcontract_id, vendor_rut, project_id, contrato, fecha, monto_total, moneda, pagado
- v_subcontratos_ep: subcontract_id, periodo, avance_pct, monto_bruto, retenciones, monto_neto, estado

### Operaciones Obra

- v_diario_obra_resumen: report_id, project_id, fecha, actividades, avance_pct, cuadrilla_size
- v_avance_fotos: project_id, fecha, url, tags, descripcion
- v_gps_trazas: project_id, fecha_hora, lat, lon, device_id

### Documentos & IA

- v_documentos_busqueda: document_id, project_id, title, doc_type, version, status, created_at
- v_doc_embeddings_meta: document_id, chunk_count, last_indexed
- v_rfi_pendientes: rfi_id, project_id, numero, titulo, solicitante, responsable, fecha_solicitud, estado
- v_rfi_respuestas: rfi_id, fecha_respuesta, respondido_por, contenido

### Riesgos & HSE

- v_riesgos_resumen: project_id, riesgo, probabilidad, impacto, nivel, estado, owner
- v_riesgos_predicciones: project_id, categoria, score, detalle, fecha_modelo, version_modelo
- v_hse_resumen: project_id, incidentes, inspecciones, cumplimiento_epp_pct, ult_incidente_fecha

### Cliente

- v_cliente_proyectos: client_id, cliente_nombre, project_id, proyecto, estado, presupuesto, compras, ventas, margen

### Admin

- v_usuarios_activos: user_id, email, name, roles, last_session

### Conciliación (snapshot opcional)

- v_conciliacion_sugerencias: suggestion_id, source_type, source_id, target_type, target_id, rule, score, status, tolerancias, created_at

## Relaciones clave

- projects ↔ purchase_orders_unified (zoho_project_id/name → project_id); vendors_unified.rut_clean ↔ purchase_orders_unified.vendor_rut; customers.rut_clean ↔ sales_invoices.customer_rut; bank_accounts ↔ bank_movements; subcontracts ↔ subcontract_progress; rfi_requests ↔ rfi_responses; documents ↔ doc_embeddings.
- project_aliases: mapping lógico entre nombres de proyecto heterogéneos; se aplica en endpoints de control financiero para consolidar claves.

## Índices recomendados

- purchase_orders_unified: (vendor_rut), (po_date), UNIQUE(zoho_po_id), UNIQUE(vendor_rut, po_number, po_date, total_amount)
- purchase_lines_unified: (po_id), UNIQUE(po_id, zoho_line_id)
- sales_invoices: (customer_rut), (invoice_date), UNIQUE(dte_id)
- bank_movements: (fecha), (account_number), (referencia), UNIQUE(external_id)
- projects: UNIQUE(zoho_project_id), UNIQUE(analytic_code)

## Gobernanza

- Vistas canónicas se crean con herramientas oficiales (no editar en prod): tools/create_finance_views.py y tools/schema.sql.
- Cambios de esquema requieren RFC y actualización de este documento.

## Endpoints relevantes (APIs)

- GET /api/projects/control
  - Devuelve: { projects: [{ project_name, budget_cost, committed, available_conservative, flags[] }] }
  - Fuentes: presupuestos (proyectos+v_presupuesto_totales) y purchase_orders_unified. Aplica alias de project_aliases cuando corresponde.
- POST /api/aliases/project
  - Body: { from: string, to: string }
  - Efecto: upsert lógico (INSERT OR IGNORE) en project_aliases para consolidar nombres heterogéneos.
- GET /api/proyectos/\<id\>/resumen
  - Devuelve: { project_id, proyecto?, presupuesto?, compras?, ventas?, margen, avance?, riesgo? }

## UI referencial

- Página /proyectos/control: listado con PC, OC y Disponible por proyecto, con enlaces a detalle.
- Página /proyectos/[project]/control: detalle por proyecto con barras tipo waterfall y alertas básicas.

