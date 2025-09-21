# Conciliación - Configuración y Observabilidad

Este documento resume las variables de entorno, constantes y campos de estado expuestos por el subsistema de conciliación (`conciliacion_api`).

## Variables de Entorno

| Variable | Default | Rango / Notas |
|----------|---------|---------------|
| `RECON_ALIAS_MAX_LEN` | 120 | Clamp 10..512. Longitud máxima para `alias` y `canonical`. |
| `RECON_SUGGEST_MIN_LIMIT` | 1 | Clamp 1..10. Límite inferior solicitable en `/suggest`. |
| `RECON_SUGGEST_MAX_LIMIT` | 50 | Clamp >= min, máx 100. Límite superior solicitable. |
| `RECON_SUGGEST_DEFAULT_LIMIT` | 5 | Autoclavado entre min y max. Valor por defecto cuando no se especifica `limit`. |
| `RECON_DISABLE_METRICS` | (unset) | Si = `1`, deshabilita `/api/conciliacion/metrics` y `/api/conciliacion/metrics/reset` (dev / entornos restringidos). |
| `RECON_LATENCY_BUCKETS` | (unset) | Lista separada por comas de límites (segundos) para histograma de latencia. Ej: `0.002,0.004,0.008`. Si inválido o vacío se usan buckets por defecto. |
| `RECON_LATENCY_SLO_P95` | (unset) | Objetivo p95 (segundos); si >0 expone gauges SLO y violación. |
| `RECON_METRICS_DEBUG` | (unset) | Si = `1` habilita endpoint debug `/api/conciliacion/metrics/latencies`. |
| `RECON_METRICS_DEBUG_TOKEN` | (unset) | Si se define y `RECON_METRICS_DEBUG=1`, requiere token (header `X-Admin-Token` o query `?token=`) para el endpoint debug. |
| `RECON_LATENCY_PERSIST_PATH` | (unset) | Ruta a archivo JSON para persistir ventana de latencias y contador SLO (se carga al iniciar el proceso y se sobrescribe tras cada muestra/reset). |
| `RECON_LATENCY_PERSIST_COMPRESS` | (unset) | Si = `1`, persiste el snapshot como `PATH.gz` usando gzip. Lectura soporta ambas variantes. |
| `RECON_LATENCY_PERSIST_EVERY_N` | 1 | Flushea a disco sólo cada N muestras nuevas (throttle). Mínimo 1. |
| `RECON_LATENCY_PERSIST_INTERVAL_SEC` | 0 | Si > 0, intervalo máximo (segundos) entre flush aunque no se alcance `EVERY_N`. 0 desactiva control por tiempo. |

## Constantes Importadas

Definidas en `backend/recon_constants.py` y recalculadas en arranque (o import). Se leen una vez por proceso.

- `ALIAS_MAX_LEN`
- `SUGGEST_MIN_LIMIT`
- `SUGGEST_MAX_LIMIT`
- `SUGGEST_DEFAULT_LIMIT`

## Endpoint `/api/conciliacion/suggest`

Respuesta ahora incluye metadatos de límites:

```jsonc
{
  "items": [...],
  "limit_used": 5,
  "limit_min": 1,
  "limit_max": 50,
  "limit_default": 5
}
```

## Endpoint `/api/conciliacion/status`

Campos de observabilidad:

| Campo | Descripción |
|-------|-------------|
| `engine_available` | Si el motor (rapidfuzz + lógica) está importable. |
| `adapter_available` | Si el adaptador externo de sugerencias está disponible. |
| `version` | Versión detectada del paquete relevante (o `unknown`). |
| `alias_max_len` | Longitud efectiva configurada. |
| `suggest_limit_min` | Límite mínimo permitido. |
| `suggest_limit_max` | Límite máximo permitido. |
| `suggest_limit_default` | Límite por defecto aplicado. |
| `alias_length_violation_count` | Número de filas en `recon_aliases` que exceden la longitud configurada; `-1` si hubo error al medir. |
| `reconciliations_count` | Total de filas en `recon_reconciliations` (o -1 si error). |
| `recon_links_count` | Total de filas en `recon_links` (o -1 si error). |

## Endpoint `/api/conciliacion/metrics`

Formato Prometheus (text/plain; version=0.0.4). Métricas actuales:

- `recon_engine_available` (gauge)
- `recon_adapter_available` (gauge)
- `recon_alias_max_len` (gauge)
- `recon_suggest_limit_min` (gauge)
- `recon_suggest_limit_max` (gauge)
- `recon_suggest_limit_default` (gauge)
- `recon_alias_length_violation_count` (gauge)
- `recon_reconciliations_total` (gauge)
- `recon_links_total` (gauge)
- `recon_suggest_latency_seconds_count` (summary - número de requests /suggest observadas)
- `recon_suggest_latency_seconds_sum` (summary - suma de segundos totales)
- `recon_suggest_latency_seconds_avg` (summary - promedio simple sobre ventana)
- `recon_suggest_latency_seconds_p95` (summary - percentil aproximado 95 sobre ventana)
- `recon_suggest_latency_seconds_histogram_bucket{le="..."}` (histograma acumulativo ventana)
- `recon_suggest_latency_seconds_histogram_count` / `recon_suggest_latency_seconds_histogram_sum`
- `recon_suggest_latency_last_reset_timestamp` (timestamp UNIX del último reset de latencias)
- `recon_suggest_latency_window_size` (muestras actuales en la ventana)
- `recon_suggest_latency_window_utilization_percent` (uso % de la ventana de latencias)
- `recon_suggest_requests_per_minute` (requests /suggest últimos 60s)
- `recon_suggest_latency_p95_slo` (valor objetivo p95 configurado)
- `recon_suggest_latency_p95_violation` (1 si p95 > SLO, 0 en caso contrario)
- `recon_suggest_latency_p95_violation_ratio` (fracción de muestras en la ventana que superan el SLO)
- `recon_suggest_latency_p95_violation_total` (contador acumulado de muestras que excedieron el SLO desde arranque o último reset)
- `recon_suggest_latency_persist_file_bytes` (tamaño en bytes del archivo de persistencia si está habilitado)
- `recon_suggest_latency_snapshot_age_seconds` (edad en segundos desde última modificación del archivo persistido)
- `recon_suggest_latency_persist_pending_samples` (muestras acumuladas en memoria aún no flushadas – útil para ajustar throttle)
- `recon_suggest_engine_success_total` (contador de ejecuciones de motor de sugerencias exitosas)
- `recon_suggest_engine_fallback_total` (contador de fallbacks: error o no disponibilidad del motor → lista vacía)

Ejemplo (recortado):

```text
# HELP recon_engine_available 1 if reconciliation engine import succeeded
# TYPE recon_engine_available gauge
recon_engine_available 1
...
```

## Reset de Métricas de Latencia

`POST /api/conciliacion/metrics/reset`

Requiere:

- Variable `RECON_METRICS_RESET_TOKEN` definida.
- Token idéntico en header `X-Admin-Token` o JSON `{ "token": "..." }`.

Ejemplo respuesta:

```jsonc
{
  "ok": true,
  "before": 18,
  "after": 0,
  "window_max": 500,
  "buckets": [0.001,0.003,0.005,0.01,0.02,0.05,0.1,0.25,0.5,1.0]
}
```

## Métrica `alias_length_violation_count`

Cuenta cuántas filas en la tabla `recon_aliases` tienen `alias` o `canonical` con longitud estrictamente mayor que `ALIAS_MAX_LEN` (valor efectivo tras clamps y lectura de `RECON_ALIAS_MAX_LEN`).

Detalles:

- Se calcula tanto en `/api/conciliacion/status` como en `/api/conciliacion/metrics` (gauge `recon_alias_length_violation_count`).
- Valor `-1` indica error al ejecutar la consulta (no debería ocurrir de forma normal; revisar logs si sucede).
- No se hace truncado automático: la métrica es diagnóstica para decidir migraciones controladas.

Acciones recomendadas si el valor > 0 tras reducir el límite:

1. Exportar filas problemáticas: `SELECT * FROM recon_aliases WHERE LENGTH(alias) > ? OR LENGTH(canonical) > ?` usando el valor efectivo.
2. Analizar si la información extra es ruido (p.ej. sufijos redundantes, texto legal repetitivo) y diseñar una función de normalización.
3. Ejecutar script de migración que aplique truncado inteligente / normalización (evitar cortar en medio de multibyte si se usan UTF-8 extendidos).
4. Re-evaluar la métrica; debería volver a 0. Documentar la decisión en CHANGELOG.

Considerar alertar si el valor se mantiene > 0 durante N días, ya que implica que entradas nuevas siguen superando el límite y tal vez falten validaciones en el flujo de ingestión.

## Endpoint Debug de Latencias

`GET /api/conciliacion/metrics/latencies` (requiere `RECON_METRICS_DEBUG=1`)

Parámetros:

- `limit` (opcional): número de muestras más recientes.
- `token` (si `RECON_METRICS_DEBUG_TOKEN` está configurado): debe coincidir con el valor definido.

Respuesta:

```jsonc
{
  "count": 25,
  "window_max": 500,
  "latencies": [0.00123, 0.00098, ...]
}
```

### Snapshot Persistido

`GET /api/conciliacion/metrics/latencies/snapshot` (requiere `RECON_METRICS_DEBUG=1` y token si definido)

Devuelve el contenido del archivo (`RECON_LATENCY_PERSIST_PATH`) si existe y no está vacío; en caso contrario un snapshot vivo (`source: "live"`).

Campos:

- `latencies`: lista de muestras (segundos)
- `slo_violation_total`: contador acumulado
- `last_reset`: timestamp del último reset
- `version`: versión del formato (1)
- `source`: `live` sólo si no había snapshot persistido disponible

### Purga de Snapshot

`DELETE /api/conciliacion/metrics/latencies/snapshot` (debug + token) elimina el archivo (`.json` o `.json.gz`). Parámetros:

- `token` (query o header) si se configuró `RECON_METRICS_DEBUG_TOKEN`.
- `clear=1` opcional: además limpia la ventana en memoria (difiere de `/metrics/reset` porque no actualiza `last_reset` ni reinicia contador SLO).

Respuesta:

```jsonc
{ "ok": true, "removed": true, "cleared_memory": false }
```

Útil para detectar necesidad de migraciones o limpieza si se reduce `ALIAS_MAX_LEN`. Si es > 0 tras bajar el límite:

1. Exportar filas largas.
2. Analizar necesidad de truncado / normalización.
3. Aplicar script de migración (manual o programado) antes de imponer restricciones más estrictas.

## Recomendaciones Operacionales

- Mantener `RECON_SUGGEST_MAX_LIMIT` en valores moderados (<=50) para evitar respuesta pesada y scans amplios.
- Aumentar `RECON_ALIAS_MAX_LEN` sólo si se evidencia pérdida semántica; revisar primero violaciones.
- Monitorear periódicamente `/api/conciliacion/status` y exportar métricas a observabilidad (Prometheus / logs estructurados) si se incorpora un collector.
- Si se requiere continuidad histórica de latencias entre reinicios, establecer `RECON_LATENCY_PERSIST_PATH` apuntando a un volumen persistente. El archivo se escribe de forma atómica (tempfile + replace) para minimizar corrupción.

## Futuras Extensiones (Ideas)

- Persistir histogramas con buckets configurables vía env.
- Exportar métricas a un registry estándar (`prometheus_client`) si se extiende.
- Alertar sobre p95 > umbral (ej. 0.25s) o bucket alto saturado.
