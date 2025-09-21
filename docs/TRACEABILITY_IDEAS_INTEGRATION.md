# Ofitec.ai — Traceability Matrix (ideas → code)

Fecha: 2025-09-15

Este documento mapea línea a línea a nivel de entregables los principales archivos bajo `ideas/*` con los artefactos implementados (endpoints, páginas, componentes, scripts) en este repositorio. También marca brechas y próximos pasos.

Nota: Muchas fuentes en `ideas/*` son especificaciones de alto nivel. Cuando el dato/vista no existe en SQLite, los endpoints implementan fallbacks seguros para mantener el contrato estable con el frontend.

---

## ideas/dashboard

- ofitec_ceo_dashboard_payload_builder_sqlite_api_5555.md
  - Backend
    - `backend/server.py` → `GET /api/ceo/overview` (payload completo con fallbacks)
    - Alias de contrato en español: además de `actions`, se entrega `acciones`
  - Script CLI
    - `tools/build_ceo_overview_payload.py` → Genera `data/ceo_overview.json` desde SQLite (mismas consultas y fallbacks)
  - Frontend
    - `frontend/app/ceo/overview/page.tsx` → Sección CEO con KPIs, Working Capital, Backlog, Margen, Salud, Riesgos y Acciones
    - `frontend/lib/api.ts` → `fetchCeoOverview()` normaliza datos (month/ytd, alerts/actions, etc.)
    - Componentes: `components/ui/KpiCard.tsx`, `components/ui/ActionsList.tsx`
  - Estado: DONE (con placeholders conscientes para margin/working_cap/backlog hasta cargar datos reales)

- ofitec_ui_overviews_proyectos_y_finanzas_react_next_tailwind_recharts.md
  - Backend
    - `backend/server.py` → `GET /api/projects/overview`, `GET /api/finance/overview`
  - Frontend
    - `frontend/app/proyectos/overview/page.tsx`, `frontend/app/finanzas/overview/page.tsx`
    - Componentes de dashboard: `KpiCard`, `Sparkline`, `StackedBar`, `ActionsList`
  - Estado: DONE (sparklines y stacked bars listos para series reales cuando existan)

- ofitec_landings_por_modulo_proyectos_y_finanzas_dashboard_kpi_especificacion.md
  - Navegación/UX
    - `frontend/components/layout/Sidebar.tsx` → Menú colapsable; al click en padre abre/cierra y navega a su overview
    - `frontend/next.config.js` → Redirects establecidos y rewrites a backend vía `BACKEND_URL`
  - Estado: DONE

- ofitec_terminologia_ui_cobros_pagos_sidebar_redirects*.md
  - Redirects: `/finanzas/cobros → /finanzas/facturas-venta`, `/finanzas/pagos → /finanzas/facturas-compra`, `/ → /ceo/overview`
  - Estado: DONE

---

## ideas/control_financiero

- ofitec_control_financiero_360_especificacion_implementacion.md
  - Backend
    - `backend/server.py` → `GET /api/projects/control?with_meta=1` (budget_cost vs committed vs available_conservative)
    - `backend/server.py` → `POST /api/aliases/project` (alias mínimo en memoria, idempotente para tests)
    - `backend/server.py` → `GET /api/projects_v2` (paginación/filtros y composición desde `purchase_orders_unified` + mapas)
    - Finanzas canónicas: `GET /api/finanzas/facturas_compra`, `GET /api/finanzas/facturas_venta`, `GET /api/finanzas/cartola_bancaria`
  - Herramientas
    - Numeración OC: `backend/server.py` helpers `_po_next_number`, `_po_peek_number`; scripts relacionados en `tools/manage_po_numbering.py`
  - Estado: DONE (baseline). Pendientes menores: persistir alias a archivo/tabla (hoy en memoria), ampliar filtros/joins por convenciones de proyecto.

- ofitec_sqlite_views.sql / ofitec_sqlite_extras.sql
  - Dependencias esperadas por endpoints: `v_presupuesto_totales`, `v_facturas_venta`, `v_facturas_compra`, `v_ordenes_compra`, etc.
  - Estado: Se usan si existen; si faltan, se aplican fallbacks (0s, aproximaciones desde `purchase_orders_unified`/`bank_movements`).

- ofitec_postman_collection.json
  - Estado: No requerida en runtime; endpoints implementan los contratos especificados.

- OFITEC_Copilot_Handoff_Control_Financiero.md / OFITEC_Guia_Control_Proyectos_Codex.md
  - Estado: Entregables cubiertos con endpoints y vistas overview; scripts DB utilitarios en `tools/*` para setup y verificación (`verify_schema.py`, `apply_schema.py`, `setup_db.py`).

---

## ideas/contratistas

- ofitec_plan_tecnico_grn_recepciones_subcontratos_avances_retenciones_portal_de_pagos.md
  - Backend
    - `backend/sc_ep_api.py` (Blueprint `sc_ep`)
      - Tablas: `sc_ep_headers`, `sc_ep_lines`, `sc_ep_deductions`, `sc_ep_files`
      - Endpoints: `GET /api/sc/ep`, `POST /api/sc/ep`, `GET /api/sc/ep/<id>`, `PUT /api/sc/ep/<id>`, `POST /api/sc/ep/<id>/lines/bulk`, `POST /api/sc/ep/<id>/deductions/bulk`, `GET /api/sc/ep/<id>/summary`, `POST /api/sc/ep/import`, `GET /api/sc/ping`
  - Frontend
    - `frontend/app/proyectos/subcontratistas/page.tsx` → Listado de EP SC (recientes), DataTable
  - Estado: DONE (núcleo SC EP). Pendiente: GRN/recepciones para SC (vista específica no implementada aún).

- ofitec_addenda_postgres_ui_chips_badges.md
  - Estado: Badges/Chips de addendas no implementados en UI (pendiente de fuente y diseño). Se puede añadir en la tabla SC EP cuando haya fuente.

---

## ideas/estado_de_pago

- ofitec_entregables_ep_sql_api_flask_react_wizard.md
  - Backend
    - Blueprint EP cliente (disponible si `ep_api.py` existe; el server lo registra de forma tolerante)
    - Métricas WIP EP en `/api/projects/overview` (`ep_headers` si existen)
  - Frontend
    - Wizard EP cliente descrito: base cubierta por páginas de proyectos; wizard completo a definir tras consolidar esquema definitivo y relaciones EP→FV
  - Estado: PARCIAL (SC EP listo; EP cliente base, faltan enlaces a FV para cierre 100%)

- ofitec_playbook_estados_de_pago_cliente_integracion_ventas_flujo.md
  - Estado: PARCIAL. Integración EP→FV aún no consolidada (se sugiere vista/tabla puente y KPI de `wip_ep_to_invoice`).

- Documento 002-837-107-3.pdf
  - Referencial (no ejecutable). Estado: N/A.

---

## ideas/proyectos

- ofitec_entregables_modulo_proyecto_open_api_sql_react.md
  - Backend
    - `GET /api/projects`, `GET /api/projects_v2` (consolidación por proyecto, paginación y metadatos)
  - Frontend
    - `frontend/app/proyectos/overview/page.tsx` (portafolio con KPIs y salud)
  - Estado: DONE

- Ofitec_Modulo_Proyectos_Presupuestos_Guia_Codex*.md
  - Backend/DB
    - Uso de `v_presupuesto_totales` para PC; KPI `without_pc` implementado
  - Estado: DONE (KPI base). Pendiente: `on_budget/over_budget` desde vista `v_project_financial_kpis` o equivalente.

- ofitec_schema.sql, ofitec_import_templates.*
  - Soporte: `tools/apply_schema.py`, `tools/verify_schema.py`, `tools/setup_db.py` y utilitarios ETL (`tools/etl_common.py`, importadores varios)
  - Estado: Herramientas listas; aplicar según dataset final.

---

## Gaps y próximos pasos

- Working Capital expandido (cash d7/d30/d60/d90, CCC real): requiere conciliación y obligaciones (nómina, impuestos, AP programados). Endpoint listo para recibir los campos.
- Proyectos on_budget/over_budget: depender de `v_project_financial_kpis` o cálculo reconciliado PC vs AP (no OC). KPI placeholder hoy.
- 3‑Way match y violaciones: requerir `v_3way_status_po_line_ext` (o similar). KPI placeholder hoy.
- EP cliente → FV (ventas): agregar KPI `wip_ep_to_invoice` real (ahora existe capa intermedia Nota de Venta).
- Contratistas Addendas chips/badges UI: pendiente de fuente y diseño minimal.
- Persistir aliases de proyecto: hoy en memoria; llevar a tabla `project_aliases` o JSON bajo `backend/` para durabilidad.
- QA scripts extra: añadir consultas auxiliares en `scripts/` para verificación rápida de vistas (algunas ya en `scripts/` existentes).
- Documentar guía Quickstart (AGREGADO: `QUICKSTART.md`).
- Normalizar códigos de error (AGREGADO: `API_ERROR_CODES.md`).
- Añadir pruebas de Nota de Venta y retenciones multi-EP (AGREGADO: `test_sales_note_flow.py`, `test_ep_retention_multi_integration.py`).

---

## Pruebas y estabilidad

- Tests backend
  - `backend/tests/test_api_contracts.py` (contratos generales)
  - `backend/tests/test_overview_endpoints.py` (overview Projects/Finance/CEO)
  - `backend/tests/test_control_financiero.py` (projects/control y aliases)
  - Resultado actual: PASS (11/11)

- Build/Runtime
  - Puertos respetados: Backend 5555, Frontend 3001
  - Rewrites: `frontend/next.config.js` → `/api/* → BACKEND_URL` (en Docker apunta a `http://backend:5555`)
  - Home → `/ceo/overview` por redirect

---

## Referencias rápidas (QA)

- BD y rutas: `GET /api/admin/db`, `GET /api/admin/routes`
- CEO payload: `GET /api/ceo/overview` o generar `tools/build_ceo_overview_payload.py`
- SC EP módulo: `GET /api/sc/ping`, `GET /api/sc/ep?limit=50`
- Control financiero: `GET /api/projects/control?with_meta=1`
