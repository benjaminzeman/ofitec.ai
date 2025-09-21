# Canonical DB and Operations Guide

This document describes the canonical database used by ofitec.ai, how the backend exposes data, and the basic operations to validate the system locally.

## Ports and Services

- Backend API: <http://localhost:5555/api>
- Frontend (Next.js): <http://localhost:3001>
- Health endpoint: <http://localhost:5555/api/status>

## Canonical Database

- File: `ofitec.ai/data/chipax_data.db` (e.g., `c:\Odoo\custom_addons\ofitec.ai\data\chipax_data.db`).
- Purpose: single source of truth for financial/project purchasing data.
- Validation helper: `tools/dev/introspect_chipax.py` prints tables, schema, and sample aggregates.

### Key Tables

Only the relevant, confirmed tables are listed here to avoid confusion. Use the introspection tool to see the full set on your machine.

- purchase_orders_unified
  - confirmed columns (subset):
    - vendor_rut
    - zoho_vendor_name
    - zoho_project_name
    - po_number
    - po_date
    - total_amount
  - role: authoritative view of POs merged from upstream sources (Zoho/Chipax pipeline).

- proveedores_unificados
  - role: unified supplier registry referenced by POs.

- purchase_lines_unified (if present)
  - role: item-level lines for POs. Not currently required by the UI dashboards.

- zoho_purchase_orders_unified (staging/reference)
  - role: staging/reference for Zoho-originated POs.

Note: A table named `chipax_facturas` is NOT present in the canonical DB. All current financial views are derived from purchase orders.

## Backend Endpoints (Flask)

The backend uses `chipax_data.db` as the real data source. Core endpoints:

- GET /api/status
  - Uptime, DB connectivity check, and `chipax_data.db` size/exists info.

- GET /api/projects
  - Aggregates from `purchase_orders_unified` grouped by `zoho_project_name`.
  - Returns counts, total_amount, and date span for each project.

- GET /api/providers
  - Aggregates from `purchase_orders_unified` grouped by `vendor_rut, zoho_vendor_name`.
  - Returns number of POs, latest `po_date`, and `SUM(total_amount)`.

- GET /api/financial
  - Computes a financial summary using purchase orders as spend.
  - Returns a `summary` object and a `recentMovements` list (built from `po_date`, amount, and vendor).

### Purchase Orders (Ofitec)

- GET `/api/purchase_orders` (list)
  - Supports `page`, `page_size`, filters (`vendor_rut`, `project`, `date_from`, `date_to`, `search`).
- POST `/api/purchase_orders` (create header)
  - Body (min): `vendor_rut`, `po_date`, `total_amount`.
  - Optional: `vendor_name`, `currency`, `status`, `project_name`, `project_id`, `manual_number`.
  - Behavior: if `po_number` is not provided, generates Ofitec sequential from `ofitec_sequences` (prefix/padding configurable).
- GET `/api/purchase_orders/<id>` (detail)
  - Returns header and lines.
- GET `/api/purchase_orders/<id>/lines`, POST to add lines
  - Line fields: `item_name`, `item_desc`, `quantity`, `unit_price`, `line_total?`, `currency?`, `uom?`, `tax_percent?`, `tax_amount?`, `status?`.
- GET `/api/purchase_orders/peek_number`
  - Returns `{ next_number }` without incrementing the sequence.

### Conciliación

- POST `/api/conciliacion/sugerencias`
  - Body: `{ source_type: 'bank'|'purchase'|'sales'|'expense', id?: number, amount?: number, date?: 'YYYY-MM-DD', ref?: string, currency?: string, days?: number, amount_tol?: number, targets?: string[] }`
  - Returns: `{ items: [ { target_kind, view, doc, fecha, amount, currency, score }... ], meta: { total } }`
  - Origen típico: botón en cartola/facturas/gastos/ventas. No persiste; sólo entrega candidatos.
- POST `/api/conciliacion/confirmar`
  - Body: `{ source_type, source_ref|source_id, target_type, target_ref|target_id, metadata? }`
  - Proxy a servicio externo (URL en `CONCILIACION_SERVICE_URL`). Si no está configurado, responde 202 con `service:false`.

## Canonical Finance Views (Finanzas)

To standardize access for Finance pages, the following database views are defined (see Ley de Base de Datos, Artículo IX):

- v_facturas_compra: proxy mapped from `purchase_orders_unified` until DTE ingestion is available.
- v_facturas_venta: placeholder (empty) until sales ingestion is available.
- v_gastos: placeholder.
- v_impuestos: placeholder.
- v_previred: placeholder.
- v_sueldos: placeholder.
- v_cartola_bancaria: placeholder.

Creation is handled by `tools/create_finance_views.py` and is idempotent. Do not hand-edit views in production; use the tool.

## Frontend Wiring (Next.js)

- API base configured to `http://localhost:5555/api` in `ofitec.ai/web/lib/api.ts`.
- The Finanzas page maps `/api/financial` to its local view model; when the API is unavailable it falls back to mock data with a clear message.

## How to Validate Locally

1. Check health

- Open <http://localhost:5555/api/status> in a browser or REST client. Confirm `ok: true` and DB details.

1. Inspect DB (optional)

- Run the helper `tools/dev/introspect_chipax.py` to list tables and counts.

### Initialize or Refresh the Canonical DB

- Apply schema (tables + base views):
  - `python ofitec.ai/tools/apply_schema.py`
- Create/refresh Finance canonical views:
  - `python ofitec.ai/tools/create_finance_views.py`
- Verify required tables/views exist:
  - `python ofitec.ai/tools/verify_schema.py`

Notes:
- All tools honor `DB_PATH`. Default DB path is `ofitec.ai/data/chipax_data.db`.

### Module Ingestion (Finance)

- Expenses → `expenses` → `v_gastos`
  - `python ofitec.ai/tools/import_expenses.py --csv data/gastos.csv`
- Taxes → `taxes` → `v_impuestos`
  - `python ofitec.ai/tools/import_taxes.py --csv data/impuestos.csv`
- Previred → `previred_contributions` → `v_previred`
  - `python ofitec.ai/tools/import_previred.py --csv data/previred.csv`
- Payroll → `payroll_slips` → `v_sueldos`
  - `python ofitec.ai/tools/import_payroll.py --csv data/sueldos.csv`
- Bank Accounts → `bank_accounts` (tesorería)
  - `python ofitec.ai/tools/import_bank_accounts.py --csv data/cuentas.csv`

After ingesting, run:
- `python ofitec.ai/tools/create_finance_views.py`
- `python ofitec.ai/tools/verify_schema.py`
- `python ofitec.ai/tools/quality_report.py`

One-shot setup:
- `python ofitec.ai/tools/setup_db.py`
- With quality report: `python ofitec.ai/tools/setup_db.py --with-quality-report`

### Purchase Orders Numbering (Ofitec)

- Sequence table: `ofitec_sequences` with `name='po_number'` stores prefix/padding/next_value.
- Configure sequence:
  - Peek next: `python ofitec.ai/tools/manage_po_numbering.py --peek`
  - Set prefix/padding/start: `python ofitec.ai/tools/manage_po_numbering.py --set-prefix PO- --set-padding 5 --set-start 1`
- Create PO with Ofitec number:
  - `python ofitec.ai/tools/create_purchase_order.py --vendor-rut 76262345-9 --vendor-name "Proveedor S.A." --total 123456.78`
  - Manual override: add `--manual-number PO-MANUAL-001`
- Import from Zoho (default keeps Zoho number). A future flag will allow Ofitec numbering on import while preserving `zoho_po_id`.

### Data Quality & RUT Validation

- Importers validate/normalize Chilean RUTs (DV check):
  - `import_expenses.py`, `import_previred.py`, `import_payroll.py`.
  - Default behavior: reject invalid RUTs (skip rows) and report counts.
  - Allow invalids (not recommended): add `--allow-invalid-rut`.
- All importers print a summary: inserted, duplicates skipped, invalid_rut.

### Migrations

- Align `purchase_lines_unified` with `po_id` column and indexes:
  - `python ofitec.ai/tools/migrate_purchase_lines_po_id.py`
  - Adds `po_id` if missing and ensures indexes. Does not backfill `po_id` for legacy rows.
- You may also pass `--db` explicitly to each command.

1. Open the dashboard

- Navigate to <http://localhost:3001> and verify dashboard widgets populate. Finanzas and Proyectos should reflect data from `purchase_orders_unified`.

## Operational Notes

- Single canonical data file: `chipax_data.db`. Avoid introducing new ad-hoc files.
- Legacy scripts are archived under `archive/db_legacy/`. Do not invoke them in production or dev flows. If needed, port logic into `tools/` with tests.
- Formatting:
  - Python follows a strict line-length limit (79 chars) to match current lint rules.
  - Prefer small functions and explicit SQL with named columns.

## Troubleshooting

- `no such table` errors
  - Verify `chipax_data.db` exists and contains the mentioned tables using `tools/introspect_chipax.py`.
- Financial or providers endpoint returns unexpected data
  - Confirm the presence of `zoho_vendor_name`, `vendor_rut`, `zoho_project_name`, `po_date`, `total_amount` in `purchase_orders_unified`.
- Frontend requests fail
  - Ensure the backend is on port 5555 and CORS is enabled; check `/api/status` first.

## Roadmap (next)

- Extend `/api/financial` with monthly trends and vendor/category breakdowns from `purchase_orders_unified`.
- Add tests for endpoint contracts and DB queries.
- Document the ingestion pipeline that populates `chipax_data.db` and provide a reproducible command.

## Reconciliation (Conciliación Transversal)

Conciliation is a transversal capability. The Portal reads standardized finance views and delegates matching to the official reconciliation service:

- Source views: `v_cartola_bancaria`, `v_facturas_compra`, `v_facturas_venta`, `v_gastos`, `v_sueldos`, `v_impuestos`.
- Matching engine: `services/conciliacion_bancaria` (Flask API) provides suggestions and confirmations.
- Portal responsibilities: list/filter candidates per context, display suggestions/scores, and call the service to confirm or reject matches. The canonical persistence of reconciliations lives in the service DB, not in `chipax_data.db`.

Do not implement local, ad‑hoc matching logic in the Portal. Follow the rules in Ley de BD Artículo X.

