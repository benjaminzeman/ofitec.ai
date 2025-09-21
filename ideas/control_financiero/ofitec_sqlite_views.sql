-- Presupuesto total por proyecto
DROP VIEW IF EXISTS v_presupuesto_totales;
CREATE VIEW v_presupuesto_totales AS
SELECT
  prj.project_name,
  SUM(p.total) AS total_presupuesto
FROM proyectos_presupuestos p
JOIN proyectos prj ON prj.id = p.project_id
GROUP BY prj.project_name;

-- Comprometido (OC aprobadas)
DROP VIEW IF EXISTS v_cost_committed;
CREATE VIEW v_cost_committed AS
SELECT
  oc.zoho_project_name AS project_name,
  SUM(oc.total_amount) AS committed
FROM purchase_orders_unified oc
WHERE oc.status IN ('approved','closed')
GROUP BY oc.zoho_project_name;

-- Facturado (vista canónica)
DROP VIEW IF EXISTS v_cost_invoiced;
CREATE VIEW v_cost_invoiced AS
SELECT
  f.project_name,
  SUM(f.total_amount) AS invoiced
FROM v_facturas_compra f
GROUP BY f.project_name;

-- Pagado (conciliado)
DROP VIEW IF EXISTS v_cost_paid;
CREATE VIEW v_cost_paid AS
SELECT
  c.project_name,
  SUM(c.paid_amount) AS paid
FROM v_cartola_bancaria c
GROUP BY c.project_name;

-- Disponibles y salud
DROP VIEW IF EXISTS v_available;
CREATE VIEW v_available AS
SELECT
  pc.project_name,
  pc.total_presupuesto,
  COALESCE(co.committed,0) AS committed,
  COALESCE(iv.invoiced,0) AS invoiced,
  COALESCE(pd.paid,0) AS paid,
  (pc.total_presupuesto - COALESCE(co.committed,0)) AS available_conservative,
  (pc.total_presupuesto - COALESCE(iv.invoiced,0))  AS available_real
FROM v_presupuesto_totales pc
LEFT JOIN v_cost_committed co ON co.project_name = pc.project_name
LEFT JOIN v_cost_invoiced iv ON iv.project_name = pc.project_name
LEFT JOIN v_cost_paid pd     ON pd.project_name = pc.project_name;

-- Flags de salud
DROP VIEW IF EXISTS v_project_health_flags;
CREATE VIEW v_project_health_flags AS
SELECT
  a.project_name,
  CASE WHEN committed > total_presupuesto THEN 'exceeds_budget' END AS flag1,
  CASE WHEN invoiced  > committed         THEN 'invoice_over_po' END AS flag2,
  CASE WHEN paid      > invoiced          THEN 'overpaid'        END AS flag3
FROM v_available a;
