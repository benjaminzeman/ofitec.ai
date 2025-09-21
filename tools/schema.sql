-- ofitec.ai - Esquema canónico y vistas (DEV)
-- Ejecutar en SQLite (DEV). En PROD aplicar vía migraciones controladas.

PRAGMA foreign_keys = OFF;

-- Tablas núcleo (subset de columnas clave)
CREATE TABLE IF NOT EXISTS ofitec_sequences (
  name TEXT PRIMARY KEY,
  prefix TEXT,
  padding INTEGER DEFAULT 0,
  next_value INTEGER NOT NULL,
  enable_manual INTEGER DEFAULT 1,
  updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  zoho_project_id TEXT UNIQUE,
  name TEXT,
  client_id INTEGER,
  status TEXT,
  budget_total REAL,
  start_date TEXT,
  end_date TEXT,
  analytic_code TEXT UNIQUE,
  slug TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS vendors_unified (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rut_clean TEXT UNIQUE NOT NULL,
  name_normalized TEXT NOT NULL,
  source_platform TEXT NOT NULL,
  zoho_vendor_name TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS customers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rut_clean TEXT UNIQUE NOT NULL,
  name_normalized TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS purchase_orders_unified (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vendor_rut TEXT NOT NULL,
  zoho_vendor_name TEXT,
  po_number TEXT NOT NULL,
  po_date TEXT NOT NULL,
  total_amount REAL NOT NULL CHECK(total_amount >= 0),
  currency TEXT NOT NULL DEFAULT 'CLP',
  status TEXT NOT NULL,
  source_platform TEXT NOT NULL,
  zoho_po_id TEXT,
  zoho_project_id TEXT,
  zoho_project_name TEXT,
  exchange_rate REAL,
  migration_id TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_po_unique ON purchase_orders_unified(vendor_rut, po_number, po_date, total_amount);
CREATE INDEX IF NOT EXISTS ix_po_date ON purchase_orders_unified(po_date);
-- Enforce unique Ofitec numbers only for POs created in Ofitec
CREATE UNIQUE INDEX IF NOT EXISTS ux_po_number_ofitec
  ON purchase_orders_unified(po_number)
  WHERE source_platform IN ('ofitec_manual','ofitec_ui','ofitec_api');

CREATE TABLE IF NOT EXISTS purchase_lines_unified (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  po_id INTEGER NOT NULL,
  item_name TEXT,
  item_desc TEXT,
  quantity REAL,
  unit_price REAL,
  line_total REAL,
  currency TEXT,
  tax_percent REAL,
  tax_amount REAL,
  uom TEXT,
  status TEXT,
  zoho_line_id TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_lines_po_id ON purchase_lines_unified(po_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_lines_po_zohoid ON purchase_lines_unified(po_id, zoho_line_id);

CREATE TABLE IF NOT EXISTS sales_invoices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_rut TEXT,
  customer_name TEXT,
  invoice_number TEXT,
  invoice_date TEXT,
  total_amount REAL,
  currency TEXT,
  status TEXT,
  source_platform TEXT,
  dte_id TEXT,
  project_id INTEGER,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sales_invoice_lines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  invoice_id INTEGER NOT NULL,
  item_name TEXT,
  item_desc TEXT,
  quantity REAL,
  unit_price REAL,
  line_total REAL,
  currency TEXT,
  tax_percent REAL,
  tax_amount REAL,
  uom TEXT,
  status TEXT
);

-- Accounts Payable (AP) - Facturas de compra reales
CREATE TABLE IF NOT EXISTS ap_invoices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vendor_rut TEXT,
  vendor_name TEXT,
  invoice_number TEXT,
  invoice_date TEXT,
  due_date TEXT,
  currency TEXT DEFAULT 'CLP',
  net_amount REAL,
  tax_amount REAL,
  exempt_amount REAL,
  total_amount REAL,
  source_platform TEXT,
  source_id TEXT,
  project_name TEXT,
  status TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_ap_unique
  ON ap_invoices(vendor_rut, invoice_number, invoice_date, total_amount);

CREATE TABLE IF NOT EXISTS ap_invoice_lines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  invoice_id INTEGER NOT NULL REFERENCES ap_invoices(id) ON DELETE CASCADE,
  description TEXT,
  qty REAL,
  unit_price REAL,
  line_total REAL,
  uom TEXT,
  po_id TEXT,
  po_line_id TEXT
);

CREATE TABLE IF NOT EXISTS expenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fecha TEXT,
  categoria TEXT,
  descripcion TEXT,
  monto REAL,
  moneda TEXT,
  proveedor_rut TEXT,
  proyecto TEXT,
  fuente TEXT,
  status TEXT,
  comprobante TEXT
);

CREATE TABLE IF NOT EXISTS taxes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  periodo TEXT,
  tipo TEXT,
  monto_debito REAL,
  monto_credito REAL,
  neto REAL,
  estado TEXT,
  fecha_presentacion TEXT,
  fuente TEXT
);

CREATE TABLE IF NOT EXISTS previred_contributions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  periodo TEXT,
  rut_trabajador TEXT,
  nombre_trabajador TEXT,
  rut_empresa TEXT,
  monto_total REAL,
  estado TEXT,
  fecha_pago TEXT,
  fuente TEXT
);

CREATE TABLE IF NOT EXISTS payroll_slips (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  periodo TEXT,
  rut_trabajador TEXT,
  nombre_trabajador TEXT,
  cargo TEXT,
  bruto REAL,
  liquido REAL,
  descuentos REAL,
  fecha_pago TEXT,
  fuente TEXT
);

CREATE TABLE IF NOT EXISTS bank_accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bank_name TEXT,
  account_number TEXT,
  currency TEXT,
  holder TEXT,
  alias TEXT
);

CREATE TABLE IF NOT EXISTS bank_movements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fecha TEXT,
  bank_name TEXT,
  account_number TEXT,
  glosa TEXT,
  monto REAL,
  moneda TEXT,
  tipo TEXT,
  saldo REAL,
  referencia TEXT,
  fuente TEXT,
  external_id TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_bank_external ON bank_movements(external_id);

CREATE TABLE IF NOT EXISTS cashflow_planned (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER,
  category TEXT,
  fecha TEXT,
  monto REAL,
  moneda TEXT,
  status TEXT,
  source_ref TEXT
);

CREATE TABLE IF NOT EXISTS zoho_po_raw (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_file TEXT,
  row_index INTEGER,
  row_json TEXT,
  import_batch_id TEXT,
  hash TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS projects_analytic_map (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  zoho_project_id TEXT UNIQUE,
  zoho_project_name TEXT,
  analytic_code TEXT,
  slug TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

-- (Se omiten por brevedad definiciones de subcontracts, daily_reports, documents, rfi, hse, risk, admin …
--  Siguen el esquema declarado en DB_CANONICA_Y_VISTAS.md)

-- Vistas canónicas (usar herramientas oficiales para recrearlas)
DROP VIEW IF EXISTS v_facturas_compra;
CREATE VIEW v_facturas_compra AS
SELECT
  invoice_number AS documento_numero,
  invoice_date   AS fecha,
  vendor_rut     AS proveedor_rut,
  COALESCE(vendor_name, vendor_rut) AS proveedor_nombre,
  total_amount   AS monto_total,
  COALESCE(currency, 'CLP') AS moneda,
  COALESCE(status, 'open')  AS estado,
  COALESCE(source_platform, 'unknown') AS fuente
FROM ap_invoices;

DROP VIEW IF EXISTS v_facturas_venta;
CREATE VIEW v_facturas_venta AS
SELECT
  invoice_number AS documento_numero,
  invoice_date AS fecha,
  customer_rut AS cliente_rut,
  customer_name AS cliente_nombre,
  total_amount AS monto_total,
  COALESCE(currency, 'CLP') AS moneda,
  COALESCE(status, 'unknown') AS estado,
  COALESCE(source_platform, 'unknown') AS fuente
FROM sales_invoices
WHERE 1=1;

DROP VIEW IF EXISTS v_gastos;
CREATE VIEW v_gastos AS
SELECT
  CAST(id AS TEXT) AS gasto_id,
  fecha,
  categoria,
  descripcion,
  monto,
  moneda,
  proveedor_rut,
  proyecto,
  fuente
FROM expenses;

DROP VIEW IF EXISTS v_impuestos;
CREATE VIEW v_impuestos AS
SELECT periodo, tipo, monto_debito, monto_credito, neto, estado, fecha_presentacion, fuente
FROM taxes;

DROP VIEW IF EXISTS v_previred;
CREATE VIEW v_previred AS
SELECT periodo, rut_trabajador, nombre_trabajador, rut_empresa, monto_total, estado, fecha_pago, fuente
FROM previred_contributions;

DROP VIEW IF EXISTS v_sueldos;
CREATE VIEW v_sueldos AS
SELECT periodo, rut_trabajador, nombre_trabajador, cargo, bruto, liquido, descuentos, fecha_pago, fuente
FROM payroll_slips;

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

-- Vistas extendidas (ejemplos)
DROP VIEW IF EXISTS v_proveedores_resumen;
CREATE VIEW v_proveedores_resumen AS
SELECT vendor_rut AS proveedor_rut,
       COALESCE(zoho_vendor_name, vendor_rut) AS proveedor_nombre,
       COUNT(1) AS total_ordenes,
       SUM(COALESCE(total_amount,0)) AS monto_total,
       MAX(po_date) AS ultima_orden
FROM purchase_orders_unified
GROUP BY vendor_rut, proveedor_nombre;

DROP VIEW IF EXISTS v_proyectos_resumen;
CREATE VIEW v_proyectos_resumen AS
SELECT COALESCE(zoho_project_name,'') AS proyecto,
       zoho_project_id AS project_id,
       COUNT(1) AS total_ordenes,
       COUNT(DISTINCT vendor_rut) AS proveedores_unicos,
       SUM(COALESCE(total_amount,0)) AS monto_total,
       MIN(po_date) AS fecha_min,
       MAX(po_date) AS fecha_max
FROM purchase_orders_unified
WHERE COALESCE(zoho_project_name,'') <> ''
GROUP BY proyecto, project_id;

DROP VIEW IF EXISTS v_ordenes_compra;
CREATE VIEW v_ordenes_compra AS
SELECT id AS oc_id, po_number, po_date AS fecha, vendor_rut AS proveedor_rut,
       COALESCE(zoho_vendor_name, vendor_rut) AS proveedor_nombre,
       total_amount AS monto_total, currency AS moneda, status AS estado,
       zoho_project_name AS proyecto, zoho_project_id AS project_id,
       source_platform AS fuente
FROM purchase_orders_unified;

DROP VIEW IF EXISTS v_ordenes_compra_lineas;
CREATE VIEW v_ordenes_compra_lineas AS
SELECT po_id AS oc_id, id AS linea_id, item_name, item_desc, quantity, unit_price, line_total, currency, uom, status
FROM purchase_lines_unified;

-- Placeholders de otras vistas (definiciones completas en DB_CANONICA_Y_VISTAS.md)
DROP VIEW IF EXISTS v_tesoreria_saldos_consolidados;
CREATE VIEW v_tesoreria_saldos_consolidados AS SELECT NULL AS banco, NULL AS cuenta, NULL AS moneda, NULL AS saldo_actual, NULL AS movimientos_30d WHERE 1=0;

DROP VIEW IF EXISTS v_cashflow_semana;
CREATE VIEW v_cashflow_semana AS SELECT NULL AS semana, NULL AS categoria, NULL AS monto, NULL AS moneda, NULL AS status WHERE 1=0;

DROP VIEW IF EXISTS v_proyectos_kpis;
CREATE VIEW v_proyectos_kpis AS SELECT NULL AS project_id, NULL AS proyecto, NULL AS presupuesto, NULL AS compras, NULL AS ventas, NULL AS margen, NULL AS avance, NULL AS riesgo WHERE 1=0;

DROP VIEW IF EXISTS v_subcontratos_resumen;
CREATE VIEW v_subcontratos_resumen AS SELECT NULL AS subcontract_id, NULL AS vendor_rut, NULL AS project_id, NULL AS contrato, NULL AS fecha, NULL AS monto_total, NULL AS moneda, NULL AS pagado WHERE 1=0;

DROP VIEW IF EXISTS v_subcontratos_ep;
CREATE VIEW v_subcontratos_ep AS SELECT NULL AS subcontract_id, NULL AS periodo, NULL AS avance_pct, NULL AS monto_bruto, NULL AS retenciones, NULL AS monto_neto, NULL AS estado WHERE 1=0;

DROP VIEW IF EXISTS v_diario_obra_resumen;
CREATE VIEW v_diario_obra_resumen AS SELECT NULL AS report_id, NULL AS project_id, NULL AS fecha, NULL AS actividades, NULL AS avance_pct, NULL AS cuadrilla_size WHERE 1=0;

DROP VIEW IF EXISTS v_avance_fotos;
CREATE VIEW v_avance_fotos AS SELECT NULL AS project_id, NULL AS fecha, NULL AS url, NULL AS tags, NULL AS descripcion WHERE 1=0;

DROP VIEW IF EXISTS v_gps_trazas;
CREATE VIEW v_gps_trazas AS SELECT NULL AS project_id, NULL AS fecha_hora, NULL AS lat, NULL AS lon, NULL AS device_id WHERE 1=0;

DROP VIEW IF EXISTS v_documentos_busqueda;
CREATE VIEW v_documentos_busqueda AS SELECT NULL AS document_id, NULL AS project_id, NULL AS title, NULL AS doc_type, NULL AS version, NULL AS status, NULL AS created_at WHERE 1=0;

DROP VIEW IF EXISTS v_doc_embeddings_meta;
CREATE VIEW v_doc_embeddings_meta AS SELECT NULL AS document_id, NULL AS chunk_count, NULL AS last_indexed WHERE 1=0;

DROP VIEW IF EXISTS v_rfi_pendientes;
CREATE VIEW v_rfi_pendientes AS SELECT NULL AS rfi_id, NULL AS project_id, NULL AS numero, NULL AS titulo, NULL AS solicitante, NULL AS responsable, NULL AS fecha_solicitud, NULL AS estado WHERE 1=0;

DROP VIEW IF EXISTS v_rfi_respuestas;
CREATE VIEW v_rfi_respuestas AS SELECT NULL AS rfi_id, NULL AS fecha_respuesta, NULL AS respondido_por, NULL AS contenido WHERE 1=0;

DROP VIEW IF EXISTS v_riesgos_resumen;
CREATE VIEW v_riesgos_resumen AS SELECT NULL AS project_id, NULL AS riesgo, NULL AS probabilidad, NULL AS impacto, NULL AS nivel, NULL AS estado, NULL AS owner WHERE 1=0;

DROP VIEW IF EXISTS v_riesgos_predicciones;
CREATE VIEW v_riesgos_predicciones AS SELECT NULL AS project_id, NULL AS categoria, NULL AS score, NULL AS detalle, NULL AS fecha_modelo, NULL AS version_modelo WHERE 1=0;

DROP VIEW IF EXISTS v_hse_resumen;
CREATE VIEW v_hse_resumen AS SELECT NULL AS project_id, NULL AS incidentes, NULL AS inspecciones, NULL AS cumplimiento_epp_pct, NULL AS ult_incidente_fecha WHERE 1=0;

DROP VIEW IF EXISTS v_cliente_proyectos;
CREATE VIEW v_cliente_proyectos AS SELECT NULL AS client_id, NULL AS cliente_nombre, NULL AS project_id, NULL AS proyecto, NULL AS estado, NULL AS presupuesto, NULL AS compras, NULL AS ventas, NULL AS margen WHERE 1=0;

DROP VIEW IF EXISTS v_usuarios_activos;
CREATE VIEW v_usuarios_activos AS SELECT NULL AS user_id, NULL AS email, NULL AS name, NULL AS roles, NULL AS last_session WHERE 1=0;

DROP VIEW IF EXISTS v_conciliacion_sugerencias;
CREATE VIEW v_conciliacion_sugerencias AS SELECT NULL AS suggestion_id, NULL AS source_type, NULL AS source_id, NULL AS target_type, NULL AS target_id, NULL AS rule, NULL AS score, NULL AS status, NULL AS tolerancias, NULL AS created_at WHERE 1=0;

PRAGMA foreign_keys = ON;


-- ==========================
-- EXTENSION: Recon/AP/AR Map
-- ==========================
-- Conciliación header + links (if not created elsewhere)
CREATE TABLE IF NOT EXISTS recon_reconciliations (
  id INTEGER PRIMARY KEY,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  context TEXT NOT NULL,
  confidence REAL,
  user_id TEXT,
  notes TEXT
);
CREATE TABLE IF NOT EXISTS recon_links (
  id INTEGER PRIMARY KEY,
  reconciliation_id INTEGER NOT NULL REFERENCES recon_reconciliations(id) ON DELETE CASCADE,
  bank_movement_id INTEGER,
  sales_invoice_id INTEGER,
  purchase_invoice_id INTEGER,
  expense_id INTEGER,
  payroll_id INTEGER,
  tax_id INTEGER,
  amount REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_links_bank ON recon_links(bank_movement_id);
CREATE INDEX IF NOT EXISTS idx_links_sales ON recon_links(sales_invoice_id);
CREATE INDEX IF NOT EXISTS idx_links_purchase ON recon_links(purchase_invoice_id);

-- Optional training/aliasing for reconciliation
CREATE TABLE IF NOT EXISTS recon_training_events (
  id INTEGER PRIMARY KEY,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  user_id TEXT,
  payload TEXT
);
CREATE TABLE IF NOT EXISTS recon_aliases (
  id INTEGER PRIMARY KEY,
  alias TEXT NOT NULL,
  canonical TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  created_by TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_recon_alias ON recon_aliases(alias);

-- AP↔PO matching persistence
CREATE TABLE IF NOT EXISTS ap_po_links (
  id INTEGER PRIMARY KEY,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  ap_invoice_id TEXT,
  po_id TEXT,
  line_id TEXT,
  amount REAL,
  user_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_ap_po_links_ap ON ap_po_links(ap_invoice_id);
CREATE INDEX IF NOT EXISTS idx_ap_po_links_po ON ap_po_links(po_id);

CREATE TABLE IF NOT EXISTS ap_match_events (
  id INTEGER PRIMARY KEY,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  user_id TEXT,
  payload TEXT
);

-- AR mapping (rules and audit)
CREATE TABLE IF NOT EXISTS ar_project_rules(
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,
  pattern TEXT NOT NULL,
  project_id TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  created_by TEXT
);
CREATE TABLE IF NOT EXISTS ar_map_events(
  id INTEGER PRIMARY KEY,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  user_id TEXT,
  payload TEXT
);

