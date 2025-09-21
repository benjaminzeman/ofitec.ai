-- ===========================
-- ofitec_sqlite_extras.sql
-- Extras mínimos para Copilot
-- ===========================

-- 1) Tabla de aliases para emparejar nombres de proyecto entre fuentes
CREATE TABLE IF NOT EXISTS project_aliases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_name TEXT NOT NULL,
  to_name   TEXT NOT NULL,
  UNIQUE(from_name, to_name)
);

-- 2) Vista de normalización de nombres de proyecto (sin tildes, lower)
--    NOTA: SQLite no tiene una función integrada para quitar tildes;
--    implementamos reemplazos básicos y dejamos el resto a la capa API si se requiere algo más robusto.
DROP VIEW IF EXISTS v_project_names_norm;
CREATE VIEW v_project_names_norm AS
SELECT
  p.project_name AS raw_name,
  LOWER(
    REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
      REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
      p.project_name,
      'Á','A'),'É','E'),'Í','I'),'Ó','O'),'Ú','U'),
      'á','a'),'é','e'),'í','i'),'ó','o'),'ú','u')
  ) AS norm_name
FROM proyectos p;

-- 3) Comprometido por proyecto (OC aprobadas/cerradas)
--    Ajusta 'status' si tu tabla purchase_orders_unified usa otros estados.
DROP VIEW IF EXISTS v_po_committed;
CREATE VIEW v_po_committed AS
SELECT
  oc.zoho_project_name AS project_name,
  SUM(oc.total_amount) AS committed
FROM purchase_orders_unified oc
WHERE COALESCE(LOWER(oc.status),'approved') IN ('approved','closed')
GROUP BY oc.zoho_project_name;

-- 4) Resumen Control Financiero (PC vs OC) SIN fallback (el fallback vive en API)
--    Asume que v_presupuesto_totales ya existe y retorna (project_name, total_presupuesto)
DROP VIEW IF EXISTS v_control_financiero_resumen;
CREATE VIEW v_control_financiero_resumen AS
SELECT
  pc.project_name,
  pc.total_presupuesto AS budget_cost,
  COALESCE(po.committed, 0) AS committed,
  (pc.total_presupuesto - COALESCE(po.committed,0)) AS available_conservative
FROM v_presupuesto_totales pc
LEFT JOIN v_po_committed po ON po.project_name = pc.project_name;
