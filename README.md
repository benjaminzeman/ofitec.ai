# ofitec.ai

![CI Tests](https://github.com/ofitec-ai/ofitec.ai/actions/workflows/tests.yml/badge.svg)

Frontend (Next.js 15) en 3001 y Backend (Flask) en 5555. Datos en `data/chipax_data.db`.
Todas las decisiones se alinean a `docs/docs_oficiales/` (Ley de Puertos, Ley de BD, Estrategias y Mapeos).

## Resumen Rápido: AP ↔ PO Matching

Módulo que sugiere y valida vínculos entre facturas de compra (AP) y líneas de OC (PO):

- Endpoints principales: `/api/ap-match/suggestions`, `/preview`, `/confirm`, `/feedback`, `/invoice/<id>`, `/config`.
- Algoritmo: selección greedy de subconjuntos + scoring (delta monto, vendor match) dentro de tolerancia.
- Validaciones: monto/qty restante, tolerancias (%), recibo requerido (3‑way-lite), sobre‑asignación.
- Tolerancias con precedencia: defaults < global < proyecto < proveedor.
- Feedback opcional persiste eventos para futura mejora de pesos.
- Migración de esquema soportada (script: `tools/migrate_ap_match_schema.py`).

Documentación completa: [docs/MATCHING.md](docs/MATCHING.md)

## Resumen: Estados de Pago (EP)

Módulo para gestionar avances de contratos cliente (EP) y su ciclo financiero:

- Tablas núcleo: contratos (`client_contracts`), SOV (`client_sov_items`), EP (`ep_headers`, `ep_lines`, `ep_deductions`), AR (`ar_invoices`, `ar_collections`), staging (`ep_import_staging`), retenciones (`ep_retention_ledger`).
- Flujo: `draft -> submitted -> approved -> invoiced -> paid`.
- Validaciones: topes SOV, duplicado de factura, neto cero, cobro excedido, violaciones en staging.
- Import Staging: heurística de mapeo de columnas y promoción a EP validado.
- Retención: cálculo sugerido y ledger para liberar en el futuro (parcial y total liberación soportadas).
- Nota de Venta (Sales Note): capa opcional previa a la factura para separar aprobación técnica de emisión tributaria.
- Métricas integradas en `/api/projects/overview` y `/api/finance/overview` (approved_net, pending_invoice, expected_inflow, actual_collections).

Detalle completo: [docs/ESTADO_PAGO.md](docs/ESTADO_PAGO.md)

Errores y convenciones de payload: [API_ERROR_CODES.md](API_ERROR_CODES.md)

Flujo EP → Nota de Venta → Factura → Cobranza mostrado en Quickstart (ver `QUICKSTART.md` cuando se agregue).

### Diagrama Flujo Comercial EP

```mermaid
flowchart LR
   A[EP draft] --> B[submitted]
   B --> C[approved]
   C --> D{Generar}
   D -->|Nota de Venta| SN[Sales Note issued]
   SN -->|Issue Invoice| I[Invoice issued]
   D -->|Factura directa| I
   I --> COL[Collections]
   COL -->|Saldo 0| P[Invoice paid]
   C -->|Retención| R[(Retention Ledger)]
   I --> R
   R --> RP[Partial Release]
   RP --> RT[Total Release]
```

## Estructura

- `frontend/`  (Next.js)
- `backend/`   (Flask API)
- `services/conciliacion_bancaria/` (servicio independiente; usar como submódulo)
- `data/`      (base de datos local, no se versiona)
- `docs/`      (docs oficiales)

## Puertos oficiales

- Frontend: <http://localhost:3001>
- Backend:  <http://localhost:5555>

### Health Check

- Backend: <http://localhost:5555/api/health> (usado en healthchecks de Docker).
- Frontend: <http://localhost:3001/api/health> (respuesta JSON `{ "status": "ok" }`).

## Primeros pasos

0. Copiar `.env.example` a `.env` y ajustar variables según tu entorno (backend, frontend y Postgres opcional).
1. Crear la base canónica (tablas + vistas) en dev:
   - `python tools/apply_schema.py --db data/chipax_data.db --schema tools/schema.sql`
   - (Alternativa solo Finanzas) `python tools/create_finance_views.py --db data/chipax_data.db`
2. Configurar `backend/.env` si deseas anular defaults:
   - `DB_PATH=../data/chipax_data.db`
   - `PORT=5555`
   - `CORS_ORIGINS=http://localhost:3001`
3. Iniciar con Docker Compose:
   - `docker-compose up --build` (usa `docker-compose.override.yml` para activar Postgres y healthchecks automáticos).
4. Endpoints principales:
   - `/api/projects`, `/api/providers`, `/api/financial`, `/api/finanzas/facturas_compra`, `/api/finanzas/cartola_bancaria`
   - EP / Estado de Pago: `/api/ep`, `/api/ep/<id>`, `/api/ep/<id>/lines/bulk`, `/api/ep/<id>/approve`, `/api/ep/<id>/generate-sales-note`, `/api/sales-notes/<sid>/issue-invoice`, `/api/ep/<id>/generate-invoice`, `/api/ep/<id>/retention/release`.
   - AP Matching: `/api/ap-match/...`
   - AR (cobranzas): `/api/ar/invoices/<id>`, `/api/ar/collections` (depende de implementación actual).
5. Frontend consume `NEXT_PUBLIC_API_BASE` (ya seteado en compose).

## Modo de Trabajo Local (histórico) vs CI Actual

Originalmente el proyecto operaba 100% en modo local (sin remoto / sin pipelines) para maximizar velocidad. Ese contexto se mantiene como referencia histórica, pero actualmente existe un workflow de GitHub Actions que ejecuta tests, quality gates y (opcionalmente) performance & stress.

Principios que se conservan localmente:

- Respaldos manuales (`scripts/backup_local.ps1`).
- Guard opcional del stub de conciliación: `python scripts/guard_conciliacion_stub.py` (ya poco necesario tras estabilizar el blueprint limpio).
- Formato y lint manual (`npm run format`, `npm run lint`).

Cambios con la introducción de CI:

- Workflow `.github/workflows/tests.yml` con jobs modulares.
- Quality gates sobre ratios y latencia.
- Tests de stress y performance opt‑in vía dispatch inputs.

Uso aislado (sin GitHub): simplemente ignora el workflow y ejecuta comandos locales como antes.

## Tests rápidos (contratos API + Pytest nuevos)

Sin dependencias extra (unittest):

Unittest legado:

```bash
python -m unittest discover -s backend/tests -v
```

Pytest (nuevos flujos: staging EP, sales notes, collections, retention multi):

```bash
python -m pytest -q
```

Tests destacados:

- `test_ep_staging_happy_path.py`
- `test_sales_note_flow.py`
- `test_ar_collections_flow.py`
- `test_ap_match_feedback_only.py`
- `test_ep_retention_multi_integration.py`

### Coverage (backend)

Script helper PowerShell:

```bash
pwsh scripts/coverage_pytest.ps1
```

Para incluir HTML:

```bash
pwsh scripts/coverage_pytest.ps1 -Html
```

El reporte HTML queda en `htmlcov/`.

## CI Automatizado & Quality Gates

Workflow principal: `.github/workflows/tests.yml` (trigger: push, pull_request, workflow_dispatch).

| Job | Propósito | Siempre | Opt‑In |
|-----|-----------|---------|--------|
| core | Suite estándar (funcional + unit) | Sí | - |
| quality-thresholds | Enforce `failure_ratio`, `drop_ratio` | Sí | - |
| perf | Benchmark p95 conciliación | No | `run_perf` |
| stress | Saturación cola async / `drop_ratio` | No | `run_stress` |

### Inputs (workflow_dispatch)

- `run_perf` (bool, default false)
- `run_stress` (bool, default false)
- `perf_budget_ms` (int, default 120)
- `max_failure_ratio` (float, default 0.15)
- `max_drop_ratio` (float, default 0.25)

Variables de entorno derivadas: `PERF_P95_BUDGET_MS`, `MAX_FAILURE_RATIO`, `MAX_DROP_RATIO`.

### Métricas controladas

- `failure_ratio` = errores / emitidos
- `drop_ratio` = dropped / intentos
- `p95_latency_ms` (solo job perf)

Si un límite se excede el job falla temprano, evitando merges regresivos.

### Marcadores Pytest

- `@pytest.mark.perf`
- `@pytest.mark.stress`

Ejecución local selectiva:

```bash
python -m pytest -m perf -q
python -m pytest -m stress -q
```

PowerShell helper:

```bash
pwsh scripts/test_select.ps1 -Markers perf
pwsh scripts/test_select.ps1 -Markers stress
```

### Artefacto de Performance

`PERF_BASELINE_JSON=perf_result.json` hace que el benchmark exporte un JSON (samples, p95_ms, avg_ms, slo_budget_ms) para publicar como artifact.

En el workflow se sube con el nombre de artifact `perf-baseline-json` y archivo `perf_result.json`. Puede descargarse desde la pestaña *Actions* para comparar historiales o generar badges.

### Historial de Performance

Además se genera/actualiza `perf_history.csv` (artifact `perf-history`) acumulando filas:

```text
timestamp,iterations,mean_ms,p95_ms,budget_ms
2025-09-20T12:34:56Z,60,11.8,33.5,120
```

Esto permite análisis de regresión temporal fuera del repositorio.

### Badge de Estado

El badge al inicio del README apunta al workflow `tests.yml` y refleja el estado del último run en branch principal.

### Job Lint/Format

Se añadió job `lint-format` que ejecuta `npm run format:check` y luego `npm run lint` (frontend). Si hay diferencias de formato, el job falla para incentivar formatear antes de merge.

### Cobertura Backend

El job `core` ahora genera `coverage.xml` y aplica un umbral mínimo configurable vía input `min_coverage` (default 70). Si la cobertura (line-rate global) cae por debajo, el job falla.

Artifacts:
 
- `coverage-backend`: incluye `coverage.xml` y `.coverage` (para análisis externo o subir a servicios de cobertura si se desea en el futuro).
 

Puedes lanzar el workflow manual con un umbral distinto, por ejemplo 75%, ajustando `min_coverage` en `workflow_dispatch`.

### Futuras extensiones sugeridas

- Badge dinámico de p95 y ratios leyendo el último artifact.
- Historial acumulado de benchmarks para detectar regresiones de tendencia.
- Job opcional de lint/format (si se reintroducen hooks estrictos).

---

## Scripts útiles

- `scripts/dev_compose_rebuild.ps1`: Rebuild y arranque de contenedores sin caché.
- `scripts/dev_rebuild_and_smoke.ps1`: Rebuild + smoke para SC EP.
- `scripts/smoke_sc_ep.ps1`: Prueba rápida del cálculo de Estado de Pago.
- `scripts/smoke_sc_ep.py`: Versión Python del smoke SC EP.
- `scripts/smoke_ar_map.ps1`: Smoke del endpoint de sugerencias AR.
- `scripts/smoke_ar_auto_assign.ps1`: Smoke del auto-asignador AR (usa `-DryRun` por defecto en la tarea).
- `scripts/promote_ar_rules.ps1`: Promueve reglas de mapeo AR aprendidas. Usa `-DryRun` para previsualizar.

## Herramientas

- `backend/reconcile_engine.py`: heurística híbrida (reglas + fuzzy) para sugerencias de conciliación y evidencias.
- `tools/import_chipax_ar.py`: Importa CSV de Chipax (AR) a `data/chipax_data.db`.
- `tools/create_finance_views.py`: Construye/actualiza vistas financieras de apoyo.
- `tools/promote_ar_rules.py`: Batch que aprende y crea reglas `ar_project_rules`.

## Convenciones de Código y Estilo

Se aplican reglas de formato y lint estrictas para asegurar consistencia.

### Formato (Prettier)

- Configuración en `frontend/.prettierrc` (ancho 100, comillas simples, trailing commas `all`).
- Ejecutar para formatear: `npm run format`.
- Verificar sin modificar: `npm run format:check`.

### Lint (ESLint)

- Script: `npm run lint` (usa ESLint CLI directamente, no `next lint` deprecado).
- Reglas extendidas: `next/core-web-vitals` + `plugin:prettier/recommended`.
- Regla `prettier/prettier` se marca como error (bloquea commit si no se formatea).
- Variables no usadas deben eliminarse o renombrarse con prefijo `_`.

### Hooks (Desactivados)

Anteriormente se usaba Husky + lint-staged; fueron removidos para simplificar. Ejecutar manualmente:

- Formato: `npm run format`
- Lint: `npm run lint`

### Estandarización Editor

- `.editorconfig` fuerza `lf`, UTF-8 e indentación de 2 espacios.

### Banner TypeScript

- Puede aparecer un banner de soporte de `@typescript-eslint` (<5.4.0). Actualmente usamos TS 5.9.x que funciona; ignorar mientras no haya issues.

### Flujo sugerido de guardado local

1. Escribe código
2. Ejecuta `npm run format` y `npm run lint`
3. Crea un respaldo: `pwsh scripts/backup_local.ps1 -IncludeCode`
4. (Opcional) Sincroniza manualmente la carpeta `backups/` a un almacenamiento externo.

## Respaldos Locales

Script: `scripts/backup_local.ps1`

Ejemplos:

- Respaldo rápido (solo DB):
  - `pwsh scripts/backup_local.ps1`
- Respaldo incluyendo código (zip backend + frontend):
  - `pwsh scripts/backup_local.ps1 -IncludeCode`
- Conservar 14 últimos respaldos:
  - `pwsh scripts/backup_local.ps1 -IncludeCode -Keep 14`

Estructura del respaldo:

```text
backups/
   20240918_101530/
      data/
         chipax_data.db
      codigo.zip (si -IncludeCode)
```

Rotación: se conservan los N más recientes (`-Keep`, default 7).

## Health Check de la Base de Datos

Script: `python tools/data_health_check.py`

Propósito: entregar una visión rápida del estado de la BD SQLite (`chipax_data.db`):

- Tablas y vistas núcleo presentes o faltantes
- Conteo de filas por tabla y rango de fechas (columna detectada: `fecha`, `invoice_date`, `po_date`)
- Índices sugeridos (heurística sobre columnas frecuentes de búsqueda)
- Fragmentación (freelist ratio) y recomendación de `VACUUM`
- Necesidad de `ANALYZE` (estadísticas ausentes)
- Resultado de `PRAGMA integrity_check`

Ejemplos:

```bash
python tools/data_health_check.py
python tools/data_health_check.py --json > health_report.json
```

Interpretación rápida:

- `freelist ratio > 0.2` y >5000 filas totales: considerar `VACUUM`.
- `analyze_last_run = null`: ejecutar `ANALYZE;` para estadísticas de planner.
- Índices sugeridos: crear sólo si hay consultas lentas sobre esa columna.

Nota: El script NO modifica la base; sólo lee metadatos y ejecuta pragmas.

## Próximos pasos sugeridos (opcionales)

- Reintroducir control de versiones si se requiere colaboración externa.
- Mantener el pipeline CI (`.github/workflows/ci.yml`) ejecutando lint y tests.
- Reforzar cobertura de tests en `frontend`.
- Documentar Quickstart (archivo pendiente `QUICKSTART.md`).
- Añadir guía resumida de módulos (índice global docs).
- Auditoría periódica de dependencias y seguridad (`npm outdated`, `npm audit`).

## Conciliación (Reconciliation) Metrics & Endpoints

La API de conciliación fue reescrita con un blueprint limpio (`conciliacion_api_clean.py`) y métricas avanzadas.

### Endpoints principales

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/conciliacion/suggest` | POST | Sugerencias para un movimiento bancario (placeholder actual). |
| `/api/conciliacion/sugerencias` | POST | Alias de `suggest`. |
| `/api/conciliacion/preview` | POST | Previsualización (no persiste). |
| `/api/conciliacion/confirmar` | POST | Crea registro mínimo `reconciliations`. |
| `/api/conciliacion/historial` | GET | Últimos 100 reconciliations. |
| `/api/conciliacion/status` | GET | Estado simple y SLO target. |
| `/api/conciliacion/healthz` | GET | Health check liviano. |
| `/api/conciliacion/metrics` | GET | Exportación texto (formato Prometheus artesanal). |
| `/api/conciliacion/metrics/prom` | GET | Exportación nativa prometheus_client (si habilitado). |
| `/api/conciliacion/metrics/reset` | POST | Resetea métricas (token opcional). |
| `/api/conciliacion/metrics/latencies` | GET | (Debug) Lista latencias en memoria. |
| `/api/conciliacion/metrics/latencies/snapshot` | GET | (Debug) Lee snapshot persistido. |
| `/api/conciliacion/metrics/latencies/snapshot` | DELETE | (Debug) Elimina snapshot persistido. |

### Variables de Entorno (todas opcionales)

| Variable | Tipo | Default | Descripción |
|----------|------|---------|-------------|
| `RECON_DISABLE_METRICS` | bool | off | Desactiva por completo la recolección. |
| `RECON_LATENCY_BUCKETS` | csv float | interno | Buckets personalizados (segundos) para histograma. |
| `RECON_LATENCY_SLO_P95` | float | 0 (off) | SLO objetivo p95; cada muestra > SLO incrementa violación. |
| `RECON_LATENCY_PERSIST_PATH` | path | (none) | Activa persistencia de latencias (JSON / JSON.GZ). |
| `RECON_LATENCY_PERSIST_COMPRESS` | bool | off | Forzar siempre GZIP (ignora umbral). |
| `RECON_LATENCY_PERSIST_COMPRESS_MIN_BYTES` | int | 4096 | Si el JSON supera este tamaño → comprimir. |
| `RECON_LATENCY_PERSIST_EVERY_N` | int | 50 | Flush cuando se acumulan N muestras. |
| `RECON_LATENCY_PERSIST_INTERVAL_SEC` | int | 60 | Flush si pasa este intervalo desde el último flush. |
| `RECON_LATENCY_WINDOW_SIZE` | int | 500 | Tamaño de ventana en memoria (clamp 50-10000). |
| `RECON_METRICS_RESET_TOKEN` | string | (none) | Requerido en header/query para reset si se define. |
| `RECON_METRICS_DEBUG` | bool | off | Habilita endpoints de debug. |
| `RECON_METRICS_DEBUG_TOKEN` | string | (none) | Token para debug (si definido, se exige). |
| `RECON_PROM_CLIENT` | bool | off | Activa endpoint nativo `/metrics/prom`. |
| `RECONCILIACION_CLEAN` | bool | off | Fuerza a usar el módulo limpio ignorando legacy. |

## Matching Metrics (AP & AR)

KPIs ligeros para monitorear el estado de los flujos de matching de compras (AP) y asignación de proyecto (AR). Implementado en `backend/api_matching_metrics.py`.

### Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/matching/metrics` | GET | Resumen combinado AP + AR (+ cache in‑memory 30s). |
| `/api/matching/metrics/projects` | GET | Distribución de facturas por `project_id`. |
| `/api/matching/metrics/prom` | GET | Exportación nativa Prometheus (gauges) para dashboards. |

Parámetros query soportados:

- `window_days` (int >=0): Limita los conteos a registros cuya `created_at` cae dentro de los últimos N días. `0` (default) = sin filtro temporal.
- `top` (int 0..50): Cantidad de proyectos top a retornar en `top_projects` (solo `/api/matching/metrics`). Default 5. Con `0` se omite la lista.

Caching: Resultado de `/api/matching/metrics` se guarda en memoria por `(window_days, top)` durante 30 segundos. Respuestas cacheadas incluyen `"cache_hit": true`.

### Métricas Prometheus (`/api/matching/metrics/prom`)

Exporta gauges de bajo costo para scraping (no histogramas todavía). Naming estable con prefijo `matching_`:

AP:

- `matching_generation_ms` (duración generación última respuesta no-cache)
- `matching_window_days`, `matching_top`
- `matching_ap_events_total`
- `matching_ap_accepted_total`
- `matching_ap_acceptance_rate`
- `matching_ap_total_links`
- `matching_ap_distinct_invoices_linked`
- `matching_ap_avg_links_per_invoice`
- `matching_ap_candidates_avg`
- `matching_ap_confidence_acc_avg`
- `matching_ap_confidence_rej_avg`
- `matching_ap_confidence_p50`
- `matching_ap_confidence_p95` (percentil 95 derivado directamente de eventos recientes (≤5000))
- `matching_ap_confidence_p99` (percentil 99 derivado directamente de eventos recientes (≤5000); puede ser igual a p95 si pocos eventos)
- `matching_ap_confidence_bucket{range="00000_02000"}` (series) Distribución de confianza en buckets estáticos centralizados (`AP_CONFIDENCE_BUCKET_EDGES`).
- `matching_ap_confidence_bucket{range="<bucket>"}`
- `matching_ap_confidence_hist_bucket{le="<bound>"}` (cumulative estilo histogram Prom — reconstruido a partir de buckets discretos)
- `matching_ap_confidence_count`
- `matching_ap_confidence_sum` (suma EXACTA de confidencias si advanced ON; si advanced OFF se aproxima usando el punto medio de cada bucket)
- `matching_ap_confidence_p95_bucket` (p95 aproximado derivado del límite superior del primer bucket cuyo acumulado ≥95%; puede diferir ligeramente de `matching_ap_confidence_p95` que se basa en la lista raw)
- `matching_ap_confidence_p99_bucket` (p99 aproximado derivado del límite superior del primer bucket cuyo acumulado ≥99%)

AR:

- `matching_ar_events_total`
- `matching_ar_rules_total`
- `matching_ar_invoices_total`
- `matching_ar_invoices_with_project`
- `matching_ar_project_assign_rate`
- `matching_ar_patterns_distinct`
- `matching_ar_rules_project_coverage`
- `matching_ar_top_project_count{project_id="<id>"}` (una serie por proyecto top)
- `matching_ar_top_project_share{project_id="<id>"}`

Cache (booleano representado como 1/0):

- `matching_cache_hit`

Buckets de confianza (`matching_ap_confidence_bucket`):
Variable de entorno para costo:

`MATCHING_AP_ADVANCED=0` desactiva:

- Parseo de `candidates_json` (no hay `matching_ap_candidates_avg`).
- Cálculo de distribución de buckets (`matching_ap_confidence_bucket*`, `matching_ap_confidence_hist_bucket*`).
- Percentiles y promedios avanzados de confianza (`matching_ap_confidence_acc_avg`, `matching_ap_confidence_rej_avg`, `matching_ap_confidence_p50`, `matching_ap_confidence_p95`, `matching_ap_confidence_p95_bucket`, `matching_ap_confidence_p99`, `matching_ap_confidence_p99_bucket`).
- Suma exacta de confianza; en este modo si aún se emite `matching_ap_confidence_sum` proviene de la aproximación por midpoint de buckets previos en cache (si existía) o no se expone.

Queda siempre disponible lo básico: totales, aceptación, links y métricas AR. Cualquier valor distinto a `0,false,no,off` lo habilita (default habilitado).

Se generan series etiquetadas con `range` que representan el conteo de eventos AP en intervalos acumulativos estilo histogram (límite superior inclusivo). Rango textual se construye concatenando bordes con formato `00_02` implicando `[0.00, 0.20]`.

Orden y bordes actuales (pueden extenderse sin breaking change). Se centralizan en `backend/recon_constants.py` (`AP_CONFIDENCE_BUCKET_EDGES`):

| range label | Intervalo confianza <= |
|-------------|------------------------|
| `00000_02000` | 0.20 |
| `02000_04000` | 0.40 |
| `04000_06000` | 0.60 |
| `06000_08000` | 0.80 |
| `08000_09000` | 0.90 |
| `09000_09500` | 0.95 |
| `09500_10000` | 1.00 |

Ejemplo de scrape (parcial) incluyendo p95 derivado de buckets y suma exacta:

```text
# HELP matching_ap_confidence_bucket Count of events by confidence bucket (le-style textual range)
# TYPE matching_ap_confidence_bucket gauge
matching_ap_confidence_bucket{range="00000_02000"} 3
matching_ap_confidence_bucket{range="02000_04000"} 7
matching_ap_confidence_bucket{range="04000_06000"} 11
matching_ap_confidence_bucket{range="06000_08000"} 5
matching_ap_confidence_bucket{range="08000_09000"} 2
matching_ap_confidence_bucket{range="09000_09500"} 1
matching_ap_confidence_bucket{range="09500_10000"} 4
# HELP matching_ap_confidence_p95_bucket Approximate p95 confidence from bucket upper bound
matching_ap_confidence_p95_bucket 0.9500
# HELP matching_ap_confidence_sum Exact (or approximated) sum of confidence values
matching_ap_confidence_sum 12.3456
```

Notas:

- Cada evento cae exactamente en el primer bucket cuyo borde superior es >= confianza.
- Si no hay eventos, no se exportan series (evita ruido en dashboards).
- Añadir nuevos buckets (p.ej. subdividir >0.95) no rompe queries existentes (paneles que agregan por label `range` se adaptan automáticamente). Si se modifica la lista se recomienda actualizar dashboards para anotar el cambio.

Notas:

- Sólo se materializa un set de gauges por scrape; los valores reflejan la última ejecución de `/api/matching/metrics` (se fuerza refresco interno cuando el TTL expiró).
- Campos null en JSON se omiten (no se exponen gauges) para evitar ruido (ej: `acceptance_rate` cuando no hay eventos).
- El histograma cumulativo expuesto se deriva de los buckets y no reintroduce costos O(n) adicionales fuera del muestreo ya realizado.

### Diferencia entre `matching_ap_confidence_p95` / `p99` y sus variantes bucket

- `matching_ap_confidence_p95` / `p99`: Calculados ordenando hasta 5000 eventos recientes y tomando índices posicionales → más precisos pero requieren leer confidencias individuales (gated por `MATCHING_AP_ADVANCED`).
- `matching_ap_confidence_p95_bucket` / `p99_bucket`: Aproximaciones rápidas basadas sólo en la distribución de buckets (eligen el límite superior del primer bucket cuyo acumulado ≥95% / ≥99%). Estables frente a cambios de granularidad (añadir buckets refina, no rompe).

Recomendación:

- Usar `matching_ap_confidence_p95` para alertas de degradación (más sensible) y `matching_ap_confidence_p95_bucket` para panel base en dashboards o fallback si se desactiva advanced.
- Emplear `matching_ap_confidence_p99` para detectar colas largas de baja confianza (siempre validar volumen de eventos; con muestras escasas p99≈p95) y `matching_ap_confidence_p99_bucket` como vista agregada menos costosa.

### Respuesta `/api/matching/metrics`

Campos de primer nivel:

- `generated_at` (UTC ISO, segundo precision)
- `generation_ms` (int) duración de la generación (excluye serialización Flask)
- `window_days` (int)
- `top` (int solicitado)
- `cache_hit` (bool, sólo presente si proviene de cache)
- `ap` (obj)
- `ar` (obj)

Objeto `ap`:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `events_total` | int | Cantidad de filas en `ap_match_events` (filtradas por ventana si aplica). |
| `accepted_total` | int | Eventos aceptados (`accepted=1`) si la columna existe. |
| `acceptance_rate` | float/null | `accepted_total / events_total` (4 decimales). Null si `events_total=0`. |
| `total_links` | int | Filas en `ap_po_links` dentro de la ventana. |
| `distinct_invoices_linked` | int | Facturas únicas con al menos un vínculo. |
| `avg_links_per_invoice` | float | Promedio `total_links / distinct_invoices_linked` (2 decimales). |
| `last_event_at` | str/null | Máximo `created_at` en `ap_match_events`. |
| `last_link_at` | str/null | Máximo `created_at` en `ap_po_links`. |
| `candidates_avg` | float/null | Promedio de largo de `candidates_json` (subset ≤5000 eventos recientes). |
| `confidence_acc_avg` | float/null | Promedio confianza eventos aceptados (4 dec). |
| `confidence_rej_avg` | float/null | Promedio confianza eventos rechazados. |
| `confidence_p50` | float/null | Mediana de `confidence`. |
| `confidence_p95` | float/null | Percentil 95 aproximado. |
| `confidence_p99` | float/null | Percentil 99 aproximado (puede igualar p95 si n bajo). |

Objeto `ar`:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `events_total` | int | Cantidad de filas en `ar_map_events` (ventana). |
| `rules_total` | int | Reglas en `ar_project_rules`. |
| `invoices_total` | int | Filas en `sales_invoices` (ventana). |
| `invoices_with_project` | int | Facturas con `project_id` no vacío. |
| `project_assign_rate` | float/null | Proporción facturas con proyecto. |
| `last_event_at` | str/null | Último evento AR. |
| `patterns_distinct` | int | Distintos patrones en reglas. |
| `rules_project_coverage` | float/null | `patterns_distinct / rules_total` (4 dec) o null si 0 reglas. |
| `top_projects` | lista/null | Lista de objetos `{project_id, count, share}` o null si `top=0` o sin datos. |

### Respuesta `/api/matching/metrics/projects`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `items` | lista | Cada item `{project_id, count, share}` ordenado por `count` desc. |
| `total` | int | Total facturas en la ventana (todas, con y sin proyecto). |
| `window_days` | int | Eco del parámetro. |

### Notas de Diseño

- El endpoint tolera ausencia de tablas devolviendo ceros / nulls (facilita despliegues graduales).
- Se evita cargar todos los eventos para métricas de confianza: se limita a 5000 últimos para costo O(1) acotado.
- Cálculo de p95: índice `int(0.95 * (n-1))` sobre lista ordenada (suficiente para dashboard rápido).
- `rules_project_coverage` busca indicar diversidad de patrones vs total de reglas.
- Futuras extensiones posibles: buckets de confianza, histograma de candidatos, evolución temporal (serie). Añadir nuevos campos no rompe compatibilidad.

### Métricas (Texto `/metrics`)

Ejemplo (parcial):

```text
recon_suggest_latency_seconds_count 42
recon_suggest_latency_seconds_sum 0.523781000
recon_suggest_latency_seconds_avg 0.012471
recon_suggest_latency_seconds_p95 0.045000
recon_suggest_latency_bucket{le="0.010000"} 30
recon_suggest_latency_bucket{le="0.050000"} 42
recon_suggest_latency_bucket{le="+Inf"} 42
recon_suggest_slo_p95_violation_total 3
recon_engine_success_total 10
recon_engine_fallback_total 5
recon_engine_error_total 1
recon_engine_empty_total 26
recon_engine_success_ratio 0.2381
...
```

### Métricas (Prom nativo `/metrics/prom`)

Incluye gauges / histogram reconstruido en memoria:

- `recon_suggest_latency_seconds` (Histogram)
- `recon_suggest_latency_avg_seconds`, `recon_suggest_latency_p95_seconds`
- `recon_suggest_latency_count`, `recon_suggest_latency_sum_seconds`
- `recon_engine_<outcome>` (gauges por ventana) y ratios `recon_engine_<outcome>_ratio`
- `recon_engine_requests_total`
- `recon_suggest_slo_p95_violation_total`
- `recon_requests_per_second_60s`, `recon_requests_per_second_300s`
- `recon_window_size`, `recon_latency_window_filled`
- Persistencia: `flushes`, `force_compress`, `compress_min_bytes` + gauges:
   `recon_persist_pending_samples`, `recon_persist_flush_total`, `recon_persist_last_flush_age_seconds`, `recon_persist_force_compress`, `recon_persist_compress_min_bytes`, `recon_persist_last_size_bytes`, `recon_persist_last_raw_bytes`, `recon_persist_last_compression_ratio`, `recon_persist_error_total`

### Persistencia

Cuando se define `RECON_LATENCY_PERSIST_PATH`, cada flush escribe un snapshot JSON (o GZIP) con las latencias actuales:

```json
{
   "ts": 1737061234.123,
   "latencies": [0.012, 0.030, 0.004]
}
```

Flush triggers:

- Cada `RECON_LATENCY_PERSIST_EVERY_N` muestras
- O si pasó `RECON_LATENCY_PERSIST_INTERVAL_SEC` segundos desde el último flush
- O si se llama a reset con persistencia activa

Compresión: forzada si `RECON_LATENCY_PERSIST_COMPRESS=1` o si el tamaño sin comprimir ≥ `RECON_LATENCY_PERSIST_COMPRESS_MIN_BYTES`.

### Ratios & SLO

- Los ratios de engine son instantáneos sobre la ventana (no acumulativos globales).
- El p95 nunca se reporta menor al promedio (si p95 < avg se ajusta a avg para evitar saltos paradoxales en gráficos).
- Violaciones SLO incrementan por cada muestra individual que excede el target (`RECON_LATENCY_SLO_P95`).

### Reset seguro

`POST /api/conciliacion/metrics/reset` limpia ventana y contadores. Si se define `RECON_METRICS_RESET_TOKEN`, requiere header `X-Reset-Token` o query `?token=` coincidente.

---

### CHANGELOG (Resumen rápido de esta iteración)

- Reemplazo completo de `conciliacion_api.py` por módulo limpio (`conciliacion_api_clean.py`).
- Métricas: summary, histogram manual, p95 SLO + violaciones, ratios engine.
- Persistencia JSON/GZIP adaptativa (size threshold + forced mode + every_n/interval triggers).
- Endpoints de debug (latencies, snapshot get/delete) y reset con token.
- Exportación Prometheus texto + endpoint nativo enriquecido (histogram, ratios, RPS, window sizing).
- Variables de entorno documentadas y gating del módulo limpio (`RECONCILIACION_CLEAN`).
- Añadidos contadores de flush internos (`flushes`) y metadata de compresión al payload.
- Exportadas métricas de persistencia como gauges (`recon_persist_*`).
- Añadido guard script `scripts/guard_conciliacion_stub.py` + hook local pre-commit para prevenir reaparición del legacy.
- Nuevos percentiles p50/p99, métricas de tamaño/compresión y error counter de persistencia.
- Endpoint debug `/api/conciliacion/metrics/json` y script `scripts/smoke_conciliacion_flow.py`.

#### Compatibilidad Legacy (Conciliación)

Para mantener dashboards y tests históricos mientras se adopta el blueprint limpio se añadió una capa explícita de compatibilidad:

- Módulo `backend/legacy_compat.py` centraliza lógica heredada: ensure de tablas (`recon_reconciliations`, `recon_links`, `recon_aliases`), normalización de montos negativos, truncado de alias (máx 120 chars), inserción de fila combinada y upsert manual de alias.
- Fila combinada: al confirmar una conciliación que vincula un movimiento bancario y un documento de venta (u otro par primario) se inserta además una fila "combinada" en `recon_links` para que queries legacy que esperaban una relación agregada no queden vacías.

#### Refactor Interno (Iteración Actual)

- Se extrajeron las funciones de cálculo de percentiles e histograma a `backend/metrics_utils.py` para aislar el math y facilitar pruebas unitarias futuras.
- El cliente SII (`sii_service.py`) ahora tipa `_request_rcv` devolviendo siempre `List[Dict[str,Any]]` normalizada (periodo, tipo_dte, folio, rut_emisor/rut_receptor, montos); esto reduce branches en `_normalize_rcv_payload` y elimina retornos heterogéneos (dict vs list) que complicaban los tests.
- Próximos pasos planeados: adaptadores SQLite para datetimes, test de compresión forzada `.gz` y consolidación de utilidades de métricas adicionales (si crece la superficie).

### Contrato del Cliente SII (RCV)

El módulo `backend/sii_service.py` expone un cliente `SiiClient` con los métodos públicos:

| Método | Retorno | Notas |
|--------|---------|-------|
| `fetch_rcv_sales(year, month)` | `List[Dict[str,Any]]` | Siempre lista de ítems normalizados (puede estar vacía). |
| `fetch_rcv_purchases(year, month)` | `List[Dict[str,Any]]` | Igual formato que ventas. |

Cada entrada normalizada incluye (claves posibles nulas según origen):
`periodo, rut_emisor, rut_receptor, tipo_dte, folio, fecha_emision, neto, iva, exento, total, estado_sii, xml_hash`.

Semántica especial heredada (para compatibilidad de tests legacy):

- Una respuesta HTTP 404 del endpoint remoto produce `{}` en `_request_rcv` (no lista vacía). Los métodos `fetch_rcv_*` normalizan luego a lista vacía al pasar por `_normalize_rcv_payload`.
- Respuestas exitosas (200) se unifican en una lista indexable aun si el JSON remoto no trae arreglo al nivel superior (se envuelve y se normalizan claves camelCase → snake_case parciales para `rut_emisor`, `rut_receptor`, `tipo_dte`).
- Reintentos automáticos en 401: invalida token y repite la llamada una vez; si la segunda respuesta no es 2xx/404 se propaga `HTTPError`.
- `_request_rcv` está marcado interno; el contrato estable es a través de `fetch_rcv_sales` / `fetch_rcv_purchases`.

Buenas prácticas al usarlo:

1. Configurar `SII_RUT` (`########-#`).
2. Ajustar `SII_TOKEN_TTL_MINUTES` y `SII_TOKEN_SAFETY_SECONDS` sólo en pruebas o entornos controlados.
3. Usar `SII_FAKE_MODE=1` para escenarios deterministas (fixtures locales) sin acceso real.
4. No depender del orden de las claves retornadas ni de campos opcionales ausentes; validar presencia antes de usar.

Potenciales futuras mejoras (no implementadas aún):

- Tipado con `TypedDict` para validar estructura en tiempo de análisis.
- Normalización numérica (parseo `neto`, `iva`, `total` a `float`) previa a persistencia.
- Cache local de respuestas por periodo para reducir llamadas repetidas en batch.
- Normalización negativa: montos negativos se convierten a valor absoluto para reproducir comportamiento legacy previo en `confirmar`.
- Alias truncation: cualquier alias >120 caracteres incrementa contador de violaciones y se almacena truncado, igual que antes.
- Métricas de compatibilidad agregadas al payload texto (`/api/conciliacion/metrics`) para no romper parsers existentes:
   - `recon_reconciliations_total`
   - `recon_links_total`
   - `recon_alias_max_len`
   - `recon_alias_length_violation_count`
- Código nuevo expone status code 422 en payloads inválidos (antes 400 en ciertos caminos); se añadieron tests que fijan este contrato.
- Nueva batería smoke interna: `backend/tests/test_conciliacion_smoke_internal.py` valida: (1) inserción de fila combinada, (2) normalización de montos negativos, (3) respuesta 422 en payload inválido.

Notas de diseño:

- La API limpia delega toda la parte "legacy" al módulo; facilita retiro futuro cambiando sólo un import.
- El refactor minimiza riesgo de regresión al encapsular DDL bootstrap y mutaciones en funciones puras idempotentes.

Roadmap de limpieza futura (no bloqueante):

- Eliminar líneas de métricas de compatibilidad cuando dashboards se hayan actualizado al nuevo set enriquecido.
- Unificar path movement-only y pair confirm en una sola función con validación declarativa.
- Añadir `ruff` y reglas de complejidad ciclomática en `legacy_compat.py` si crece.


### Tabla rápida de métricas clave (prefijo recon_)

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `recon_suggest_latency_seconds_count` | summary count | Número de muestras en ventana. |
| `recon_suggest_latency_seconds_sum` | summary sum | Suma de latencias ventana. |
| `recon_suggest_latency_seconds_avg` | gauge | Promedio calculado. |
| `recon_suggest_latency_seconds_p50` | gauge | P50 (percentil 50) ventana. |
| `recon_suggest_latency_seconds_p95` | gauge | P95 ajustado (>= avg). |
| `recon_suggest_latency_seconds_p99` | gauge | P99 (>= p95). |
| `recon_suggest_latency_bucket{le="..."}` | histogram | Histograma acumulado. |
| `recon_engine_success_total` etc. | gauge | Totales de outcomes en ventana. |
| `recon_engine_success_ratio` etc. | gauge | Ratios outcomes. |
| `recon_suggest_slo_p95_violation_total` | counter | Violaciones SLO p95 (muestras > target). |
| `recon_requests_per_second_60s` | gauge | RPS aproximado últimos 60s. |
| `recon_persist_flush_total` | gauge | Flushes realizados. |
| `recon_persist_last_flush_age_seconds` | gauge | Segundos desde último flush. |
| `recon_persist_pending_samples` | gauge | Muestras esperando flush. |
| `recon_persist_force_compress` | gauge | Flag compresión forzada (1/0). |
| `recon_persist_compress_min_bytes` | gauge | Umbral bytes para compresión. |
| `recon_persist_last_size_bytes` | gauge | Tamaño archivo persistido (final). |
| `recon_persist_last_raw_bytes` | gauge | Tamaño sin comprimir. |
| `recon_persist_last_compression_ratio` | gauge | Compressed/raw (<=1). |
| `recon_persist_error_total` | counter | Errores de escritura. |
| `recon_window_size` | gauge | Capacidad máxima ventana. |
| `recon_latency_window_filled` | gauge | Muestras actuales. |

### Script Smoke Conciliación

Ejecutar prueba mínima end-to-end:

```bash
python scripts/smoke_conciliacion_flow.py
```

Salida esperada incluye percentiles y gauges de persistencia.

### Nota sobre lint futuro

Se planea introducir `ruff` para homogeneizar estilo Python (reglas básicas: import order, unused, complejidad). Aún no se agrega config para no frenar flujo local; adoptar en una próxima iteración.


