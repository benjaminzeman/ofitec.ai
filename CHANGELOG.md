# Changelog - ofitec.ai

Fecha: 2025-09-18

## [2025-09-18] DB Connection Unification & Conciliación Fix

### Changed (previo 2025-09-13)

- Unificada la gestión de conexiones SQLite usando `backend.db_utils.db_conn` en:
  - `server.py` (todas las rutas migradas; eliminación de patrones manuales salvo wrapper legado `_connect_db` mantenido por compat temporal en tests y `api_ap_match`).
  - `api_sales_invoices.py` (eliminado context manager duplicado).
  - `conciliacion_api.py` (ya estaba alineado; import de `reconcile_engine` ahora es opcional para evitar fallos si falta `rapidfuzz`).
- Endpoints de órdenes de compra (`/api/purchase_orders*`) refactorizados a `with db_conn()`.

### Fixed

- Rutas `/api/conciliacion/*` devolviendo 404 por fallo en import opcional: ahora blueprint siempre se registra (fallback seguro cuando falta engine de reconciliación).

### Notes

- Test suite: 105 tests pasando tras refactor (antes 20 fallos de conciliación).
- Próximo paso sugerido: retirar `_connect_db` definitivamente tras adaptar tests de AP Match para usar sólo `db_conn`.

---

## [Unreleased]

### Added

- Integración con SII: endpoints `/api/sii/*`, almacenamiento RCV y página `/finanzas/sii` con SSE en vivo.
- AP Match test coverage: over_allocation, config precedence, invoice aggregation, amount_tol override.
- Coverage tooling via pytest-cov.
- Reconciliación: endpoint `/api/conciliacion/status` con flags `engine_available`, `adapter_available`, `version`.

#### Matching Metrics (AP & AR) Observability Enhancements

- Exacta la suma de confianza (`matching_ap_confidence_sum`) cuando `MATCHING_AP_ADVANCED` está habilitado (antes aproximada por midpoint de buckets).
- Nuevo gauge `matching_ap_confidence_p95_bucket` (p95 aproximado basado en buckets) y documentación asociada.
- Centralización de bordes de buckets de confianza en `AP_CONFIDENCE_BUCKET_EDGES` (`recon_constants.py`).
- Dashboard Grafana inicial (`docs/observability/grafana_matching_ap_dashboard.json`) con p95, sum, buckets y tasa de aceptación.
- P99 raw (`matching_ap_confidence_p99`) y aproximado por buckets (`matching_ap_confidence_p99_bucket`) añadidos para detectar colas de baja confianza.
- Archivo de reglas de alerta ejemplo (`docs/observability/prometheus_rules_matching.yml`) con condiciones sobre p95/p99 bajos y acceptance rate.
- Tests ampliados: presencia de p95/p99 (raw & bucket) y gating por `MATCHING_AP_ADVANCED`.
  
#### (Nuevo) Módulo Limpio Conciliación & Observabilidad

- Reescritura completa aislada (`conciliacion_api_clean.py`) que reemplaza la versión corrupta previa mediante import preferente en `server.py` (toggle `RECONCILIACION_CLEAN`).
- Suite de métricas avanzada (`/api/conciliacion/metrics` texto + `/api/conciliacion/metrics/prom` Prometheus nativo) con:
  - Latencias rolling (count,sum,avg,p95 no decreciente) + histograma configurable (`RECON_LATENCY_BUCKETS`).
  - SLO p95 opcional (`RECON_LATENCY_SLO_P95`) y contador de violaciones acumuladas.
  - Contadores de resultados del motor (success,fallback,error,empty) + ratios instantáneos.
  - RPS aproximado (60s/300s), utilización de ventana y tamaño actual.
  - Persistencia opcional de latencias + violaciones SLO (JSON / GZIP adaptativo) con flush por N muestras o intervalo (`RECON_LATENCY_PERSIST_*`).
  - Endpoints reset seguro y debug (latencies crudas, snapshot get/delete) protegidos por tokens (`RECON_METRICS_RESET_TOKEN`, `RECON_METRICS_DEBUG_TOKEN`).
  - Payload expone también metadatos de compresión, flushes realizados y muestras pendientes de persistir.
- Documentación detallada añadida al README (sección "Conciliación Metrics & Endpoints").

- Nuevos tests de conciliación:
  - `test_conciliacion_status_basic` (status endpoint)
  - `test_alias_truncation_and_upsert` (truncado 120 chars y upsert de alias)
  - `test_negative_amount_normalized_to_zero` (normalización de montos negativos a 0.0)
  - `test_conciliacion_historial_basic_order_and_sum` (orden y agregación monto)
  - `test_admin_routes_contains_key_endpoints` (smoke rutas críticas registradas)
  - `test_conciliacion_confirmar_requires_links_or_pair` (payload inválido 422)
  - `test_conciliacion_suggest_metadata` (metadatos de límites en suggest)
- Tests de ETL: `backend/tests/test_etl_common_parse.py` valida normalizacion numerica multi-formato.

### Changed (Refactors & Config Expansion)

- Backend SII: nuevos módulos `backend/api_sii.py` y `backend/sii_service.py` para tokens, RCV y eventos con soporte SQLite.
- Página `/finanzas/sii` incluye guía paso a paso (requisitos, operación y modo demo).
- Importadores Chipax (`tools/import_chipax_conciliacion.py`, `tools/import_chipax_ar.py`, `tools/import_bank_movements.py`) ahora usan normalizacion robusta, UPSERT idempotente y limpieza de duplicados legacy.
- `tools/etl_common.py` centraliza helpers de normalizacion y sanea columnas/indexes faltantes en SQLite antes de importar.
  - `test_conciliacion_status_metadata` (campos de límites en status)
  - `test_conciliacion_status_alias_violation_metric` (métrica de violaciones de longitud)
  - Documento `docs/CONCILIACION_CONFIG.md` (config y observabilidad conciliación)
  - Script `tools/bench_recon_links_query.py` (micro benchmark historial)
  - Endpoint `/api/conciliacion/metrics` (métricas estilo Prometheus: config y violaciones)
  - Flag `--explain` en `tools/bench_recon_links_query.py` para inspeccionar plan
  - Contadores añadidos: `/api/conciliacion/status` ahora incluye `reconciliations_count`, `recon_links_count`; `/api/conciliacion/metrics` expone `recon_reconciliations_total`, `recon_links_total`.
  - Endpoint `/api/conciliacion/healthz` (probe liviano liveness/readiness).
  - Métricas de latencia `/suggest`: `recon_suggest_latency_seconds_*` (count,sum,avg,p95) en `/api/conciliacion/metrics`; añadido histograma `recon_suggest_latency_seconds_histogram_bucket` + `_count`/`_sum`.
  - Endpoint admin `POST /api/conciliacion/metrics/reset` protegido por `RECON_METRICS_RESET_TOKEN` para reiniciar ventana de latencias.
  - Toggle `RECON_DISABLE_METRICS=1` para deshabilitar endpoints de métricas en despliegues que no exponen Prometheus.
  - Métricas adicionales: `recon_suggest_latency_last_reset_timestamp`, `recon_suggest_latency_window_size`.
  - Buckets de latencia dinámicos vía `RECON_LATENCY_BUCKETS` + gauges: `recon_suggest_latency_window_utilization_percent`, `recon_suggest_requests_per_minute`.
  - SLO opcional p95 vía `RECON_LATENCY_SLO_P95` con gauges `recon_suggest_latency_p95_slo` y `recon_suggest_latency_p95_violation`.
  - Endpoint debug `/api/conciliacion/metrics/latencies` (gated por `RECON_METRICS_DEBUG=1`) para inspección puntual de latencias crudas (limit configurable por query param).
  - Documentación ampliada de métrica `alias_length_violation_count` en `docs/CONCILIACION_CONFIG.md` (guía de remediación y consulta SQL recomendada).
  - Métricas SLO adicionales: `recon_suggest_latency_p95_violation_ratio` y `recon_suggest_latency_p95_violation_total`.
  - Token opcional `RECON_METRICS_DEBUG_TOKEN` para proteger el endpoint debug de latencias además del flag de activación.
  - Persistencia opcional de ventana de latencias y contador SLO vía `RECON_LATENCY_PERSIST_PATH` (carga al arranque y sobrescritura atómica tras cada muestra y reset).
  - Gauge de tamaño de archivo `recon_suggest_latency_persist_file_bytes` y endpoint snapshot `/api/conciliacion/metrics/latencies/snapshot` para exportar el estado persistido.
  - Gauge `recon_suggest_latency_snapshot_age_seconds` y endpoint `DELETE /api/conciliacion/metrics/latencies/snapshot` (purga opcional con `clear=1`).
  - Compresión opcional de snapshot (`RECON_LATENCY_PERSIST_COMPRESS=1`) generando `PATH.gz` (lectura transparente de `.json` o `.json.gz`).
  - Control de flush por lote `RECON_LATENCY_PERSIST_EVERY_N` y/o intervalo `RECON_LATENCY_PERSIST_INTERVAL_SEC` (reduce I/O alto en cargas intensivas).
  - Métrica `recon_suggest_latency_persist_pending_samples` exponiendo muestras aún no persistidas (diagnóstico de tuning de flush).
  - Contadores `recon_suggest_engine_success_total` y `recon_suggest_engine_fallback_total` para diferenciar ejecuciones exitosas del motor y fallbacks (errores o indisponibilidad).
  - Migración de uso de `datetime.utcnow()` a `datetime.now(UTC)` en módulos SII para manejo timezone-aware futuro.

### Changed

- Refactored `api_ap_match.py` to use shared `db_conn` context manager (removed manual connection close patterns).
- `conciliacion_api.py` already aligned on `db_conn`; validated stability with expanded test subset (20 conciliación tests passing) and added note for future connection warning cleanup elsewhere.
- Fully removed legacy `_connect_db` helper from active backend code and tests; standardized all DB access through `backend.db_utils.db_conn`. A minimal stub `backend/server_copy_tmp.py` remains only as a temporary guard (raises on use) and will be deleted after auditing external dependencies.
- `conciliacion_api.py`: factor común `_ensure_core_recon_tables` para crear tablas núcleo y reducir duplicación DDL.
- Mejorada validación en `/api/conciliacion/suggest` (sanitiza `limit`) y `/api/conciliacion/confirmar` (normaliza links, coerce montos negativos a 0, truncado de alias/canonical a 120).
- Constantes de conciliación externalizadas a `backend/recon_constants.py` con override por variables de entorno:
  - `ALIAS_MAX_LEN` (default 120, clamp 10..512)
  - `SUGGEST_MIN_LIMIT`, `SUGGEST_MAX_LIMIT`, `SUGGEST_DEFAULT_LIMIT` (defaults 1,50,5) y saneamiento central.
- Endpoint `/api/conciliacion/suggest` ahora expone metadatos de límites: `limit_used`, `limit_min`, `limit_max`, `limit_default`.
- Índices añadidos para conciliación: `ix_recon_links_reconciliation_id`, `ix_recon_links_bank_movement_id` (parcial) para acelerar consultas de historial/vínculos.
- `/api/conciliacion/status` ahora incluye `alias_max_len`, `suggest_limit_min`, `suggest_limit_max`, `suggest_limit_default` para observabilidad de configuración.

### Coverage Snapshot

- Overall backend coverage ~60%; `conciliacion_api` ~97%; `api_ap_match` ~83% after new tests.
- Nuevos tests elevan robustez de la capa de conciliación (alias y montos edge cases cubiertos) y añaden observabilidad (status endpoint).

## Base de Datos Canónica y Herramientas

- Unificación de ruta BD dentro del proyecto: `data/chipax_data.db`.
- Utilidad común `tools/common_db.py` para resolver `DB_PATH` y rutas por defecto.
- `tools/apply_schema.py`: ejecución resiliente por statements; ignora índices huérfanos.
- `tools/create_finance_views.py`: ahora consume tablas reales si existen (gastos, impuestos, previred, sueldos).
- `tools/verify_schema.py`: verificación de tablas/vistas requeridas.
- `tools/setup_db.py`: orquestador con opción `--with-quality-report`.
- `tools/introspect_chipax.py` y `tools/dev/list_db_views.py` movidos a `tools/dev/`.

## Ingesta Finanzas

- Nuevos importadores:
  - `tools/import_expenses.py` → expenses (idempotente por comprobante/combos) + validación RUT.
  - `tools/import_taxes.py` → taxes.
  - `tools/import_previred.py` → previred_contributions + validación RUT.
  - `tools/import_payroll.py` → payroll_slips + validación RUT.
  - `tools/import_bank_accounts.py` → bank_accounts (upsert por banco+cuenta).
- Samples CSV en `tools/samples/` con README.
- `tools/rut_utils.py`: normalización y DV de RUT.
- `tools/quality_report.py`: reporte de calidad (nulos, duplicados, RUTs invalid, fechas futuras).

## Migración y Esquema

- `tools/migrate_purchase_lines_po_id.py`: añade `po_id` a `purchase_lines_unified` y asegura índices.
- `tools/schema.sql`:
  - Tabla `ofitec_sequences` para numeración.
  - Índice único parcial `ux_po_number_ofitec` para `purchase_orders_unified(po_number)` cuando `source_platform` ∈ {'ofitec_manual','ofitec_ui','ofitec_api'}.

## Órdenes de Compra - Numeración Ofitec

- `tools/numbering.py`: utilidades ensure/next/peek para secuencias.
- `tools/manage_po_numbering.py`: CLI para configurar/ver la secuencia (`po_number`).
- `tools/create_purchase_order.py`: crea cabeceras con número Ofitec o manual.
- Backend (`backend/server.py`):
  - POST `/api/purchase_orders`: si falta `po_number`, genera correlativo Ofitec; normaliza RUT; `source_platform='ofitec_api'`.
  - GET `/api/purchase_orders` (list), GET `/api/purchase_orders/<id>` (detail), POST `/api/purchase_orders/<id>/lines` (alta líneas).
  - Helpers `_po_next_number()` y `_po_peek_number()`.

## Conciliación (estilo Chipax)

- CLI:
  - `tools/reconcile_utils.py`: sugiere candidatos (compras, ventas, gastos, impuestos, sueldos) por monto/fecha/referencia con scoring.
  - `tools/reconcile_suggest.py`: interfaz de línea de comando.
- Backend:
  - POST `/api/conciliacion/sugerencias`: entrega candidatos con puntuación.
  - POST `/api/conciliacion/confirmar`: proxy a servicio externo (`CONCILIACION_SERVICE_URL`).
- Frontend (Next.js):
  - `frontend/lib/api.ts`: `fetchReconcileSuggestions`, `confirmReconcile`.
  - `frontend/components/ReconcileModal.tsx`: modal UI reutilizable (Tailwind, acorde guía visual).
  - Botón “Conciliar” + modal en:
    - `app/finanzas/cartola-bancaria/page.tsx`
    - `app/finanzas/facturas-compra/page.tsx`
    - `app/finanzas/gastos/page.tsx`
    - `app/finanzas/facturas-venta/page.tsx`

## Documentación

- `docs/docs_oficiales/DB_SCHEMA_AND_OPS.md` actualizado:
  - Ruta canónica BD en el repo.
  - Secuencia de setup/ingesta/verificación + quality report.
  - Numeración de OCs (Ofitec) y endpoints relacionados.
  - Endpoints de Conciliación.

## Notas Operacionales

- Reiniciar backend para exponer nuevas rutas (`/api/conciliacion/*`, mejoras de `/api/purchase_orders`).
- `setup_db.py --with-quality-report` para validar schema + calidad.
- Definir `CONCILIACION_SERVICE_URL` para confirmaciones reales.

