-- Control Financiero 360 - Vista agregada por proyecto
-- Entrega KPIs completos para el tablero financiero por proyecto

DROP VIEW IF EXISTS v_project_financial_kpis;
CREATE VIEW v_project_financial_kpis AS
WITH pc AS (
  -- Presupuesto de Costos por proyecto
  SELECT project_id, SUM(total) AS pc
  FROM v_presupuesto_totales 
  GROUP BY project_id
), po AS (
  -- Órdenes de compra comprometidas por proyecto
  SELECT o.zoho_project_name AS project_name, SUM(o.total_amount) AS po_total
  FROM purchase_orders_unified o
  WHERE o.status IN ('approved', 'open', 'pending')
  GROUP BY o.zoho_project_name
), grn AS (
  -- Goods Receipt Notes (recepciones) por PO
  SELECT pol.po_id, SUM(COALESCE(v.qty_received_accum,0) * pol.unit_price) AS grn_total
  FROM purchase_order_lines pol
  LEFT JOIN v_po_line_received_accum v ON v.po_line_id = pol.po_line_id
  GROUP BY pol.po_id
), grn_by_project AS (
  -- GRN agregado por proyecto
  SELECT o.zoho_project_name AS project_name, SUM(g.grn_total) AS grn_total
  FROM grn g 
  JOIN purchase_orders_unified o ON o.po_id = g.po_id
  GROUP BY o.zoho_project_name
), ap AS (
  -- Accounts Payable - facturas de proveedores por proyecto
  SELECT o.zoho_project_name AS project_name, SUM(il.qty * il.unit_price) AS ap_facturado
  FROM invoice_lines il
  JOIN purchase_order_lines pol ON pol.po_line_id = il.po_line_id
  JOIN purchase_orders_unified o ON o.po_id = pol.po_id
  GROUP BY o.zoho_project_name
), ap_pay AS (
  -- Pagos AP realizados por proyecto
  SELECT i.project_name, SUM(p.amount) AS ap_pagado
  FROM v_ap_payments p
  JOIN v_ap_invoices_with_project i ON i.invoice_id = p.invoice_id
  GROUP BY i.project_name
), ventas AS (
  -- Ventas, Estados de Pago y Cobranzas por proyecto
  SELECT project_id, 
         SUM(total_contrato) AS contrato, 
         SUM(ep_acumulado) AS ep_acum,
         SUM(fact_venta) AS fact_venta, 
         SUM(cobrado) AS cobrado
  FROM v_projects_sales_rollup 
  GROUP BY project_id
), violations AS (
  -- Violaciones 3-way matching por proyecto (para risk score)
  SELECT o.zoho_project_name AS project_name, COUNT(*) AS viol_3way
  FROM ap_three_way_candidates atw
  JOIN purchase_orders_unified o ON o.po_id = atw.po_id
  WHERE atw.status = 'pending'
  GROUP BY o.zoho_project_name
)
SELECT
  pr.id AS project_id,
  pr.name AS project_name,
  
  -- Métricas de Costos
  COALESCE(pc.pc, 0) AS pc,
  COALESCE(po.po_total, 0) AS po_total,
  COALESCE(grn_by_project.grn_total, 0) AS grn_total,
  COALESCE(ap.ap_facturado, 0) AS ap_facturado,
  COALESCE(ap_pay.ap_pagado, 0) AS ap_pagado,
  
  -- Métricas de Ventas
  COALESCE(v.contrato, 0) AS contrato,
  COALESCE(v.ep_acum, 0) AS ep_acum,
  COALESCE(v.fact_venta, 0) AS fact_venta,
  COALESCE(v.cobrado, 0) AS cobrado,
  
  -- Métricas Derivadas
  COALESCE(pc.pc, 0) - COALESCE(po.po_total, 0) AS disponible,
  CASE 
    WHEN COALESCE(v.contrato, 0) > 0 
    THEN COALESCE(v.fact_venta, 0) - COALESCE(ap.ap_facturado, 0)  -- Margen
    ELSE COALESCE(pc.pc, 0) - COALESCE(ap.ap_facturado, 0)         -- Desvío
  END AS margen_desvio,
  
  -- Avance físico
  CASE 
    WHEN COALESCE(v.contrato, 0) > 0 
    THEN (COALESCE(v.ep_acum, 0) * 100.0) / v.contrato
    ELSE 0 
  END AS avance_fisico_pct,
  
  -- Risk Score (0-100)
  CASE 
    WHEN COALESCE(pc.pc, 0) = 0 THEN 90  -- Sin presupuesto
    WHEN COALESCE(po.po_total, 0) > COALESCE(pc.pc, 0) THEN 80  -- Sobregiro
    WHEN COALESCE(violations.viol_3way, 0) > 5 THEN 70  -- Muchas violaciones
    WHEN COALESCE(ap.ap_facturado, 0) > COALESCE(pc.pc, 0) * 1.1 THEN 60  -- Desvío >10%
    ELSE 20  -- Normal
  END AS risk_score,
  
  -- Contadores para chips
  COALESCE(violations.viol_3way, 0) AS viol_3way,
  
  -- Timestamps
  datetime('now') AS computed_at
  
FROM projects pr
LEFT JOIN pc ON pc.project_id = pr.id
LEFT JOIN po ON po.project_name = pr.name
LEFT JOIN grn_by_project ON grn_by_project.project_name = pr.name
LEFT JOIN ap ON ap.project_name = pr.name
LEFT JOIN ap_pay ON ap_pay.project_name = pr.name
LEFT JOIN ventas v ON v.project_id = pr.id
LEFT JOIN violations ON violations.project_name = pr.name;