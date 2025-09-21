# Structured Logs

All structured events are single-line JSON objects emitted at INFO when `RECON_STRUCTURED_LOGS=1` (or test mode) is active.
Sampling can be enabled via `RECON_STRUCTURED_LOG_SAMPLE` (float 0..1). When sampling < 1, each event is emitted with independent probability = rate.

Per-event sampling overrides: define `RECON_STRUCTURED_LOG_SAMPLE_<EVENT_NAME>` where `<EVENT_NAME>` is the upper‑cased event id with non-alphanumeric characters replaced by `_` (e.g. `recon_suggest_request` -> `RECON_STRUCTURED_LOG_SAMPLE_RECON_SUGGEST_REQUEST`). Overrides (if valid 0..1) take precedence over the global rate.

Common fields:

- event: Discriminator string.
- request_id: Correlation id. Provided by inbound `X-Request-Id` header if present, else generated (`req-<epoch_ms_hex>-<pid_hex>`).
- timestamp: RFC3339 UTC with millisecond precision (e.g. `2025-09-20T12:34:56.123Z`).
- schema_version: Integer schema version (currently 1). Bumped only for breaking changes.

Optional common field (when configured):

- debug_flags: Array of short strings copied from `RECON_DEBUG_FLAGS` (comma separated). Useful to stamp experiments or canaries.
- redaction_count: Present only when at least one field was removed due to `RECON_STRUCTURED_REDACT`; integer number of removed fields.

## Emission Counters & Gauges

JSON metrics payload (from `/api/conciliacion/metrics`) includes under `structured_logging`:

- enabled: Boolean.
- emitted_total: Count of structured events actually logged.
- sampled_out_total: Count of events skipped due to sampling probability.
- schema_version: Mirrors event schema_version.
- emit_failures_total: Count of primary emission failures (serialization) that triggered a fallback `recon_log_emit_error`.
- queue_dropped_total: (Async only) Events dropped because the async queue was full.
- failure_ratio: emit_failures_total / emitted_total (0 when emitted_total == 0).
- async_enabled: Boolean flag denoting whether async mode is active.
- async_queue_current / async_queue_max: Current queue depth and capacity (0 when async disabled).
- async_queue_utilization: Current/Max ratio (0..1) for quick saturation checks.
- drop_ratio: queue_dropped_total / (emitted_total + queue_dropped_total) (0 when denominator == 0). Proportion of potential events lost due to queue saturation.
- overrides_active_count: Number of active runtime override keys (subset of: global_sample_rate, per_event_sample, structured_logs_enabled, async_enabled).

Prometheus exposition (`/api/conciliacion/metrics/prom`) provides gauges:

- recon_structured_logging_enabled
- recon_structured_logging_emitted_total
- recon_structured_logging_sampled_out_total
- recon_structured_logging_schema_version
- recon_structured_logging_emit_failures_total
- recon_structured_logging_async_enabled
- recon_structured_logging_queue_dropped_total
- recon_structured_logging_failure_ratio
- recon_structured_logging_last_event_age_seconds (seconds since last event, -1 if none yet)
- recon_structured_logging_async_queue_current (current queue depth)
- recon_structured_logging_async_queue_max (configured queue capacity)
- recon_structured_logging_async_queue_utilization (queue depth ratio current/max)
- recon_structured_logging_drop_ratio (async drop ratio)
- recon_structured_logging_overrides_active_count (count of active runtime overrides)

All counters are process-local (reset on restart). `failure_ratio` is instantaneous.

## Events

### recon_suggest_request

Emitted after `/api/conciliacion/sugerencias`.

Fields:

- context: Normalized context or null.
- movement_id: Movement id if provided.
- limit: Effective limit.
- outcome: success | fallback | error | empty.
- latency_seconds: Wall-clock processing time.
- latency_window: Object with {count,sum,avg,p50,p95,p99} of current in-memory window.
- slo_p95_target: Current SLO threshold (seconds) or 0 if disabled.
- slo_violations_total: Total samples exceeding SLO.
- window_size: Max capacity of latency window.
- sample_count: Same as latency_window.count (float for legacy compatibility).

### recon_confirmar_request

Emitted from `/api/conciliacion/confirmar` on success.

Fields:

- variant: simple_intention | movement_only | legacy_links.
- context: Context string (may differ for movement_only path).
- movement_id: Present for movement_only variant.
- reconciliation_id: Assigned row id.
- accepted: Boolean (always true for emitted events).
- confidence: Confidence value (may be null).
- links_count: (legacy_links) Number of link rows normalized.
- alias_present: (legacy_links) Boolean whether alias supplied.
- alias_truncated: (legacy_links) Whether alias was truncated.

### recon_metrics_reset

Emitted on POST `/api/conciliacion/metrics/reset` when metrics enabled.

Fields:

- reset_at: Timestamp (seconds) when reset occurred.
- before / after: Sample counts pre/post reset.
- slo_violation_total_before / slo_violation_total_after: Violation counters.
- buckets: Active bucket list post reset.

### recon_log_emit_error

Fallback event emitted when serialization of a primary structured event fails (e.g. `json.dumps` raises). This ensures log pipelines retain visibility into failures instead of silent loss.

Fields:

- original_event: Event name that failed serialization.
- exception_class: Exception class name.
- message: Truncated exception message (<=200 chars).
- redacted_fields_attempted: Count of fields that were removed during redaction for the original event.

## Redaction

Set `RECON_STRUCTURED_REDACT` to a comma separated list of field names to drop from all structured events (after construction, before serialization). Core fields (`event,request_id,timestamp,schema_version`) are never removed.

Example:

```bash
RECON_STRUCTURED_REDACT=movement_id,limit,confidence
```

Redaction occurs uniformly; if a field is not present in a specific event it's ignored. Redaction has no side-effects on metrics.

## Debug Flags

`RECON_DEBUG_FLAGS` can contain a comma separated list of short tokens (e.g. `expA,canary1`). When present they are emitted as an array in `debug_flags` on every structured event (unless `debug_flags` itself is redacted). This provides a lightweight runtime toggle for downstream filters / dashboards without introducing per-request overhead.

## Stability & Versioning

- Fields listed are considered stable. Additions will be backward compatible (only additive).
- `schema_version` will increment only on a breaking field removal/rename or semantic change.

## Integration Guidance

- Treat numeric fields as floats (even counts can appear as 5.0 for legacy reasons).
- Parse JSON per line; ignore unknown fields for forward compatibility.
- Use `schema_version` to branch parsers if future major changes occur.
- For high-volume traffic enable sampling and rely on metrics endpoints for aggregate values.

## Future Considerations

- Potential emission of counts/ids for redaction decisions (currently only implicit via removed fields).
- Batch/async delivery mechanism.
- Optional per-event latency budget annotations.
- Config endpoint extension for future knobs (e.g. dynamic runtime changes).

## Config Endpoint

`GET /api/conciliacion/logs/config` returns runtime state & counters (only when structured logging enabled).

Example response:

```json
{
  "enabled": true,
  "schema_version": 1,
  "global_sample_rate": 0.33,
  "per_event_sample_overrides": {
    "RECON_SUGGEST_REQUEST": 0.9,
    "RECON_CONFIRMAR_REQUEST": 0.1
  },
  "redacted_fields": ["secret_field", "another"],
  "debug_flags": ["alpha", "beta"],
  "counters": {
    "emitted_total": 1205,
    "sampled_out_total": 340,
    "emit_failures_total": 2,
    "queue_dropped_total": 15,
    "async_queue_current": 42,
    "async_queue_max": 1000,
    "async_queue_utilization": 0.042,
    "drop_ratio": 0.0123,
    "overrides_active_count": 2,
    "failure_ratio": 0.0016
  },
  "env_keys": {
    "global_sample": "RECON_STRUCTURED_LOG_SAMPLE",
    "per_event_prefix": "RECON_STRUCTURED_LOG_SAMPLE_",
    "redact": "RECON_STRUCTURED_REDACT",
    "debug_flags": "RECON_DEBUG_FLAGS",
    "async_enabled": "RECON_STRUCTURED_LOG_ASYNC",
    "async_queue_size": "RECON_STRUCTURED_LOG_ASYNC_QUEUE"
  }
}
```

Notes:

- `per_event_sample_overrides` keys reflect transformed event identifiers (already uppercased / sanitized).
- Counters are process-local and reset on restart.
- Absent overrides simply do not appear in the map.
- `overrides_active_count` helps dashboards surface divergence from pure environment configuration.

### Runtime Overrides (Mutation Endpoint)

`POST /api/conciliacion/logs/runtime` allows in-memory (non-persistent) tuning without restart when structured logging is enabled.

`DELETE /api/conciliacion/logs/runtime` clears all active runtime overrides (same token security model). Response includes previous overrides:

```json
{
  "ok": true,
  "cleared": true,
  "previous_overrides": {"global_sample_rate": 0.5, "async_enabled": true}
}
```

Body fields (all optional):

```json
{
  "global_sample_rate": 0.5,
  "per_event_sample": { "RECON_SUGGEST_REQUEST": 0.9 },
  "structured_logs_enabled": true,
  "async_enabled": true
}
```

Validation:
- `global_sample_rate` float 0..1.
- Each per_event value float 0..1; event tokens sanitized automatically (non-alphanumeric -> `_`, then uppercased).
- Booleans coerced with standard JSON truthiness.

Security:
- If `RECON_RUNTIME_UPDATE_TOKEN` is set, request must include header `X-Runtime-Token: <token>` (or `X-Admin-Token`) or JSON field `token` matching the value; else 403.
- If the token env is unset the endpoint is open (still requires structured logging enabled).

Response shape:

```json
{
  "ok": true,
  "changed": {"global_sample_rate": 0.5},
  "effective_overrides": {
    "global_sample_rate": 0.5,
    "per_event_sample": {"RECON_SUGGEST_REQUEST": 0.9},
    "structured_logs_enabled": true,
    "async_enabled": true
  }
}
```

Notes:
- Overrides take precedence over environment variables for sampling and enablement decisions.
- Overrides reset on process restart (not persisted).
- Enabling async via override triggers worker initialization immediately.

## Async Logging

Set `RECON_STRUCTURED_LOG_ASYNC=1` to enable asynchronous emission. Events are enqueued into a bounded queue whose size (default 1000) can be customized via `RECON_STRUCTURED_LOG_ASYNC_QUEUE`.

Behavior:

- If the queue is full, the event is dropped silently (incrementing `queue_dropped_total`).
- Emission failures inside the worker increment `emit_failures_total` and may produce fallback events synchronously.
- Disabling async (unset or `0`) reverts to synchronous emission.

Trade-offs:

- Pros: Shields request latency from log serialization / I/O stalls.
- Cons: Potential event loss if sustained production exceeds drain capacity; ordering preserved only per process (but generally acceptable for analytics/auditing streams).

Tuning Guidelines:

- Start with default size; monitor `queue_dropped_total`, `async_queue_utilization`, `drop_ratio`, and `last_event_age_seconds`.
- If drops occur and memory headroom allows, increase queue size gradually.
- Sustained `async_queue_utilization` near 1.0 indicates saturation; consider scaling workers, increasing queue, or reducing sampling.
- Consider downstream ingestion capacity — large queues can hide back-pressure signals.

## Health Endpoint

`GET /api/conciliacion/logs/health` (only when structured logging enabled) returns:

```json
{
  "enabled": true,
  "schema_version": 1,
  "emitted_total": 1205,
  "emit_failures_total": 2,
  "sampled_out_total": 340,
  "failure_ratio": 0.0016,
  "last_event_timestamp": 1737449990.123,
  "last_event_age_seconds": 0.45,
  "async_enabled": true,
  "queue_dropped_total": 15
}
```

Usage:

- Liveness / freshness probe: alert if `last_event_age_seconds` exceeds expected bounds (requires periodic traffic).
- Error budget tracking: derive failure rate SLO via `failure_ratio`.
- Capacity monitoring: watch `queue_dropped_total` and `drop_ratio` growth rate to detect sustained overload.

If no event has ever been emitted, `last_event_timestamp` and `last_event_age_seconds` may be `null`.

## Testing Notes (Stress Metric Validation)

The test suite includes a stress-oriented test (marked `@pytest.mark.stress`) that intentionally saturates the async logging queue to assert:

- `queue_dropped_total` increments
- `drop_ratio` becomes > 0

You can skip these tests (e.g., in constrained CI) with either:

Environment variable:
```
SET SKIP_STRESS_TESTS=1  # Windows
export SKIP_STRESS_TESTS=1  # *nix
```

Or via pytest marker selection:
```
pytest -m "not stress"
```

To run only stress tests:
```
pytest -m stress -q
```

Marker is declared in `pytest.ini` for discovery.

### Performance Baseline Tests

A lightweight performance baseline test (marker `perf`) measures p95 latency of the suggest endpoint over a small sample (default 60 iterations, warmup 5). Environment variables:

- `PERF_SUGGEST_P95_BUDGET_MS` (default 120)
- `PERF_SUGGEST_ITERS` (default 60)
- `PERF_SUGGEST_WARMUP` (default 5)
- `SKIP_PERF_TESTS` (skip when set to `1|true|yes`)

Run only perf tests:
```bash
pytest -m perf -q
```

Run both perf and stress:
```bash
pytest -m "perf or stress" -q
```

Using the PowerShell helper script:
```powershell
pwsh scripts/test_select.ps1 -Perf
pwsh scripts/test_select.ps1 -Stress
pwsh scripts/test_select.ps1 -Perf -Stress
pwsh scripts/test_select.ps1 # full suite
```
