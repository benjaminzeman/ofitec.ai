# AP ↔ PO Matching Module

This document describes the end-to-end workflow, data model, algorithms, configuration precedence and API endpoints for the Accounts Payable (AP) to Purchase Order (PO) matching feature.

---

## 1. Objectives

Provide a semi‑assisted workflow that:

- Suggests optimal group(s) of PO lines covering an AP invoice amount.
- Validates quantity / amount tolerance and simple 3‑way (receipt-lite) constraints.
- Persists confirmed links.
- Captures user feedback to iteratively improve scoring.
- Supports legacy schema coexistence during migration.

---

## 2. Data Model

### 2.1 Tables

| Table | Purpose | Key Columns (Modern) |
|-------|---------|----------------------|
| `ap_po_links` | Persistent link between invoice and PO line(s) | `invoice_id, invoice_line_id (nullable), po_id, po_line_id, amount, qty, created_at, created_by` |
| `ap_match_events` | Feedback / telemetry for learning | `invoice_id, source_json, candidates_json, chosen_json, confidence, reasons, accepted, user_id, created_at` |
| `ap_match_config` | Tolerance + weight overrides | `scope_type (global/vendor/project), scope_id, amount_tol_pct, qty_tol_pct, recv_required, weight_amount_delta, weight_vendor_match, weight_history, updated_at` |

Legacy `ap_po_links` schema (auto-migrated): `id, created_at, ap_invoice_id, po_id, line_id, amount, user_id`.

Legacy `ap_match_events` schema (payload-only): `id, created_at, user_id, payload` — retained until modern form populated.

### 2.2 Analytical Views

(Names may vary by environment.)

- `v_po_line_balances_pg`: Remaining billable amount & quantity per PO line.
- `v_po_line_billed_accum_pg`: Historical billing accumulation (for coverage checks).
- `v_3way_status_po_line_ext_pg`: Enriched status with receipt / balance info.

These support validation in preview.

---

## 3. Matching Algorithm Overview

1. Fetch candidate PO lines scoped by vendor / project (heuristic filtering).
2. Score each line:
   - Vendor match bonus.
   - Amount delta score (closer to invoice residual → higher).
   - (Optional) history / frequency weight placeholder.
3. Greedy subset selection attempts to cover the target invoice amount within `amount_tol_pct`.
4. Produce ranked suggestion groups.

The approach favors simplicity + explainability and is intentionally modular for future ML/ILP optimization.

---

## 4. Tolerances & Precedence

Factors:

- `amount_tol_pct`: Allowed % deviation between sum(selected lines) and invoice amount.
- `qty_tol_pct`: Allowed % deviation between sum line quantities linked and ordered vs received/billed.
- `recv_required`: Boolean flag requiring a (simplified) received indicator when present.

Precedence resolution (lowest to highest):

1. System defaults.
2. Global override (`scope_type='global'`).
3. Project-level override (`scope_type='project'` + project id).
4. Vendor-level override (`scope_type='vendor'` + vendor id).

Resolution returns the most specific non-null value for each field.

---

## 5. Validation (Preview Phase)

Violations produced before confirmation:

- `amount_exceeds_remaining`: Selected lines exceed remaining allowed billed amount.
- `qty_exceeds_remaining`: Quantity over remaining.
- `receipt_required_missing`: `recv_required` true but line lacks receipt flag.
- `amount_out_of_tolerance`: Sum outside tolerance window.

Each violation references line(s) when applicable and is non-blocking in preview (UI decides gating rules).

---

## 6. Feedback Loop

After user confirms links, they optionally submit feedback:

- `accepted=true/false` plus reasons (array) and candidate context.
- Event persists in `ap_match_events` (modern) or legacy fallback; can inform future weight adjustments (currently manual / heuristic).

---

## 7. API Endpoints

Base path examples (Flask):

### 7.1 GET `/api/ap-match/invoice/<invoice_id>`

Returns invoice summary including existing links and amounts remaining.

### 7.2 GET `/api/ap-match/config`

Returns resolved tolerance + weight configuration (with provenance metadata if available).

### 7.3 POST `/api/ap-match/suggestions`

Body: `{ "invoice_id": <int> }`

Response: Ranked suggestion groups with candidate scoring and coverage info.

### 7.4 POST `/api/ap-match/preview`

Body: `{ "invoice_id": <int>, "links": [ {"po_id":..., "po_line_id":..., "amount": <float>, "qty": <float?> } ] }`

Response: `{ ok: true, lines: [...resolved line state...], violations: [...], tolerances: {...} }`

### 7.5 POST `/api/ap-match/confirm`

Body similar to preview with `user_id`.

Persists rows in `ap_po_links` (modern) or legacy mapping. Returns created count and echo event skeleton.

### 7.6 POST `/api/ap-match/feedback`

Body: `{ "invoice_id": int, "links": [...], "accepted": bool, "reasons": [str], "candidates": [...], "user_id": str }`

Stores an event (modern: structured columns; legacy: JSON payload wrapper).

---

## 8. Migration Strategy

A standalone script `tools/migrate_ap_match_schema.py` performs idempotent migration:

- Backs up DB file (suffix: `.pre_ap_match_migration.bak`).
- Renames legacy `ap_po_links` -> `ap_po_links_legacy_bk` and creates modern version.
- Copies forward data mapping columns (`ap_invoice_id→invoice_id`, `line_id→po_line_id`, `user_id→created_by`).
- Ensures (but does not destructively convert) modern `ap_match_events` table if legacy exists; coexistence supported.

Confirm endpoint detects actual columns via `PRAGMA` to choose modern vs fallback insert logic.

---

## 9. Error Modes & Edge Cases

| Scenario | Handling |
|----------|----------|
| Legacy table not migrated | Fallback insert path (if columns absent) |
| Missing PO line in balances view | Omitted from line validations (soft) |
| Empty suggestions | Return `suggestions: []` (UI displays no-match state) |
| Over-tolerance selection | Violation flagged; confirmation still allowed unless UI blocks |
| Duplicate link attempt | Depending on schema constraints may create parallel row (future: unique composite index advisable) |

---

## 10. Future Enhancements

- Introduce uniqueness constraint (`invoice_id + po_line_id`).
- Add `allocation_pct` + derived variance metrics.
- Incorporate historical acceptance scoring.
- Optimize subset selection using small ILP (PuLP/OR-Tools) for large invoice coverage.
- Add background job to normalize legacy event payloads into structured columns.

---

## 11. Quick Example

```bash
POST /api/ap-match/suggestions {"invoice_id": 123}
→ suggestions[0] = { lines:[{po_line_id:"L1", amount: 500}], coverage_pct: 100.0 }

POST /api/ap-match/preview {"invoice_id":123,"links":[{"po_id":77,"po_line_id":"L1","amount":500}]}
→ { ok:true, violations:[], tolerances:{amount_tol_pct:5} }

POST /api/ap-match/confirm {"invoice_id":123,"links":[{"po_id":77,"po_line_id":"L1","amount":500}],"user_id":"ana"}
→ { ok:true, links_created:1 }
```

---

## 12. Developer Notes

- Ensure analytical views exist before heavy preview usage.
- When extending scoring, keep explanation fields for transparency.
- Avoid silent migration failures—log exceptions explicitly.

---

## 13. Changelog (Module Scope)

- v1: Initial greedy + tolerance + feedback scaffold.
- v1.1: Added legacy schema migration + preview violations refinement.

---

## 14. Contact / Ownership

Primary owner: Finance Engineering Team.

Escalation: Data Platform lead if view generation fails.

