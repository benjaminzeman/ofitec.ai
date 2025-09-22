# AI Endpoints & Features

This document describes the AI-related API endpoints, behaviors, environment variables, caching, rate limiting, metrics and testing approach introduced in September 2025.

## Overview

Two primary synchronous endpoints plus one asynchronous workflow:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/ai/summary` | POST | Generate a financial / operational summary using recent AP & AR event context + metrics snapshot. |
| `/api/ai/ask` | POST | Free-form question over provided lightweight context object. |
| `/api/ai/ask/async` | POST | Start an asynchronous ask job (returns `202` + `job_id`). |
| `/api/ai/jobs/<job_id>` | GET | Poll status/result of async ask job. |

If AI is disabled (no key present or `AI_ENABLED` falsey) endpoints return `503` with `{ "error": "ai_disabled" }` (negative-path tests enforce this contract).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `XAI_API_KEY` / `GROK_API_KEY` | (unset) | Presence enables AI client (xAI Grok). If neither present and no explicit enable flag, AI is disabled. |
| `AI_ENABLED` | (derived) | Force enable (`1`, `true`) or disable (`0`, `false`) regardless of key presence (useful in tests). |
| `AI_RATE_LIMIT_WINDOW` | `60` | Sliding window size in seconds for rate limiting. |
| `AI_RATE_LIMIT_MAX` | `30` | Max calls per IP per endpoint within the sliding window. |
| `AI_SUMMARY_CACHE_TTL` | `60` | TTL in seconds for cached `/api/ai/summary` responses keyed by latest event/metric signature. |

## Rate Limiting

In-memory, per-IP & per-endpoint, sliding window using a `deque` for timestamps.

Responses when limit exceeded: `429` JSON `{ "error": "rate_limited" }` plus headers:

| Header | Meaning |
|--------|---------|
| `X-RateLimit-Limit` | Configured max calls in the window. |
| `X-RateLimit-Remaining` | Remaining quota for current window (0 when limited). |
| `X-RateLimit-Reset` | Unix epoch (approx) when quota resets (only on 429 currently). |
| `Retry-After` | Seconds to wait before retrying (computed remaining window). |
| `X-Request-ID` | Per-request correlation ID (hex, 16 chars) for tracing and log correlation (now global for all endpoints). |

## Summary Caching

`/api/ai/summary` computes a key based on the most recent AP & AR event IDs plus selected metrics counters. Cached payloads include `meta.cache = "hit" | "miss"` for observability. TTL controlled by `AI_SUMMARY_CACHE_TTL`.

Cache is in-memory only (ephemeral, process-local). Safe for single-instance dev & small deployments; consider Redis for multi-instance scale.

## Context Trimming

Large context arrays (events, feedback reasons) are trimmed before sending to the AI model:

- Maximum items per list (currently 12 for AP/AR in summary; 25 for generic ask context lists).
- Maximum string field length truncated (180 for summary, 160 for ask) with ellipsis `…`.

Helper: `_trim_events(seq, max_items, max_field)`.

## Async Ask Jobs

`POST /api/ai/ask/async` -> returns `{ job_id, status: "pending" }`.

A background thread invokes the same Grok client and updates an in-memory job store:

```json
{
  "status": "ok" | "error" | "failed" | "pending",
  "response": { ... original grok payload ... },
  "error": "<message>",
  "created_at": <ts>,
  "completed_at": <ts|null>
}
```

Polling: `GET /api/ai/jobs/<job_id>` -> `404` if not found.

Pruning: completed jobs are pruned automatically by `_prune_jobs()`:

| Env | Default | Purpose |
|-----|---------|---------|
| `AI_JOB_MAX` | `200` | Maximum retained jobs (after pruning oldest). |
| `AI_JOB_TTL_SEC` | `600` | TTL (seconds) for completed jobs; older removed first. |

Pruning runs after job completion and on new job insertion.

## Metrics (Prometheus)

Optional (import guarded):

- Counter: `ai_endpoint_calls_total{endpoint, result}` where `result` = `ok|error|disabled|rate_limited|cache_hit|cache_miss`.
- Histogram: `ai_endpoint_latency_seconds{endpoint}` (wall time for model call).
- Gauge: `ai_jobs_active` current async jobs running.
- Counter: `ai_jobs_created_total` cumulative async jobs created.
- Counter: `ai_jobs_pruned_total` jobs removed by pruning (TTL / max retention).

If `prometheus_client` missing, stub objects no-op gracefully.

Metrics are exposed at `GET /metrics` when `prometheus_client` is installed. If import fails the route logs a warning and is skipped. Scrape interval suggestion: 15s–60s depending on traffic.

### Lightweight JSON Metrics Debug Endpoint

For quick inspection without Prometheus scraping tooling, a minimal snapshot is exposed at:

`GET /api/ai/metrics/debug`

Returns JSON (fields may expand in future, avoid strict schema coupling):

```json
{
  "metrics_enabled": true,
  "jobs": { "active": 0 },
  "counters": { "calls": true, "jobs_total": true, "jobs_pruned": true }
}
```

Purpose: lightweight health/diagnostic probe for dashboards or local dev (safe: does not enumerate all sample label values, minimizing surface area).

If metrics library not available: `metrics_enabled` false; other sections may be partial.

## Error Codes

| Condition | Code | HTTP |
|-----------|------|------|
| AI disabled | `ai_disabled` | 503 |
| Missing question | `missing:question` | 422 |
| Rate limited | `rate_limited` | 429 |
| Upstream/model error | `ai_error` (generic) | 500 |

## Testing Strategy

Implemented tests:

- `test_ai_endpoints.py`: negative-path (disabled, missing question).
- `test_ai_positive.py`: positive-path summary (cache hit/miss & rate limit), ask + async job flow.
- `test_ai_ops_headers.py`: headers (rate limit, cache), and job pruning behavior.

Mocking done by monkeypatching `backend.server.grok_chat` to deterministic fakes and forcing enable via `AI_ENABLED`.

Future additions (optional):

- Metrics label counting via monkeypatching Counter/Histogram objects.
- Expiration behavior (simulate TTL expiry with time travel / monkeypatch time).
- Concurrency test for rate limiter & async jobs (multi-threaded client simulation).

## Security & Privacy Notes

- Context trimming reduces accidental leakage of large text blobs; still ensure PII minimization upstream.
- No prompt/response persistence beyond optional logging (disabled by default). Consider structured redaction if logging model prompts in production.

## Operational Considerations

| Concern | Current State | Future Option |
|---------|---------------|---------------|
| Multi-process scaling | In-memory stores not shared | External cache / Redis cluster |
| Job persistence | Lost on process restart | Durable queue (RQ / Celery / FastAPI workers) |
| Observability | Basic counters + latency | Add request IDs, per-model tokens, saturation metrics |
| Rate limiting fairness | Per-IP naive | Token bucket w/ leaky bucket + user identity |

## Quick Example (Summary)

```bash
curl -X POST http://localhost:5555/api/ai/summary -H 'Content-Type: application/json' -d '{}' | jq
```

Inspect `meta.cache` to see `hit` vs `miss`.

## Quick Example (Async Ask)

```bash
JOB=$(curl -s -X POST http://localhost:5555/api/ai/ask/async -H 'Content-Type: application/json' -d '{"question":"Hola?","context":{}}' | jq -r .job_id)
curl -s http://localhost:5555/api/ai/jobs/$JOB | jq
```

## Changelog

- 2025-09-21: Initial release (metrics, caching, rate limiting, async jobs, trimming, tests).
- 2025-09-21 (later): Added `Retry-After`, `X-Request-ID`, async job gauges/counters, pruning metrics, extended observability tests.

## Observability Additions – Summary

The second observability wave introduced:

1. Back-pressure signaling: `Retry-After` on all 429 responses (per-endpoint remaining window calculation).
2. Correlation tracing: `X-Request-ID` (16-char hex) on every AI endpoint response including errors & cache hits.
3. Async job instrumentation: real-time gauge (`ai_jobs_active`) plus cumulative counters (`ai_jobs_created_total`, `ai_jobs_pruned_total`).
4. Pruning visibility: every TTL/max removal increments `ai_jobs_pruned_total`.
5. Test coverage: header presence, uniqueness of request IDs, graceful skips when Prometheus not installed, and metrics surface assertions.

Additional (third wave) enhancements:

1. Global request correlation: `X-Request-ID` now injected for every endpoint via middleware (was AI-only).
2. Structured JSON access logging: per-request line with timestamp (`ts`), request id (`rid`), method, path, status, client IP.
3. Lightweight metrics debug endpoint: `/api/ai/metrics/debug` for quick JSON visibility without Prometheus query tooling.

These enhancements further standardize tracing and simplify local diagnostics.

Future work could extend into:

- Token usage accounting per model call.
- Distributed tracing propagation (W3C `traceparent`).
- Redaction middleware for sensitive fields.
- Externalizing in-memory stores (cache, rate limits, jobs) to Redis for multi-instance scale.
