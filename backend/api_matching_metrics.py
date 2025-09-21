"""Unified Matching Metrics Endpoint.

Exposes lightweight aggregated KPIs for AP (purchase matching) and AR (project
assignment) flows to support dashboards and CEO overview endpoints.

Route: GET /api/matching/metrics

Response JSON shape (all numeric fields are integers unless noted):
{
  "generated_at": "2025-09-20T12:34:56Z",
  "ap": {
     "events_total": 0,
     "accepted_total": 0,
     "acceptance_rate": 0.0,           # float 0..1 or null if undefined
     "total_links": 0,
     "distinct_invoices_linked": 0,
     "avg_links_per_invoice": 0.0,     # float
     "last_event_at": "2025-09-20T12:00:00" | null,
     "last_link_at": "2025-09-20T12:00:00" | null
  },
  "ar": {
     "events_total": 0,
     "rules_total": 0,
     "invoices_total": 0,
     "invoices_with_project": 0,
     "project_assign_rate": 0.0,       # float 0..1 or null
     "last_event_at": "2025-09-20T12:00:00" | null
  }
}

Design notes:
 - Each subsection returns 0 / null when source tables are absent to keep the
   contract stable and simplify front‑end handling.
 - No heavy parsing (e.g. of JSON candidate payloads) is performed in this
   first iteration; such richer metrics (avg candidates, confidence buckets)
   can be layered later without breaking backward compatibility.
 - Uses central db_conn() helper for consistent path resolution and adapters.
"""
from __future__ import annotations

from datetime import datetime, UTC
import os
from typing import Any, Dict, Tuple
import sqlite3
import json
import statistics

from flask import Blueprint, jsonify, request, current_app

from backend.db_utils import db_conn

matching_metrics_bp = Blueprint("matching_metrics", __name__)


# Simple in-memory cache: {(window_days, top): (ts_epoch, data_json_dict)}
_CACHE: dict[Tuple[int, int], tuple[float, dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = 30


def _fetch_single_value(cur: sqlite3.Cursor, sql: str, params: tuple[Any, ...] = ()) -> Any:
    try:
        cur.execute(sql, params)
        row = cur.fetchone()
        return row[0] if row else None
    except sqlite3.Error:  # table may not exist
        return None


def _ap_metrics(con: sqlite3.Connection, window_days: int) -> Dict[str, Any]:
    cur = con.cursor()
    # Detect presence of tables; if missing return zero metrics early
    try:
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ap_match_events'")
        has_events = cur.fetchone() is not None
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ap_po_links'")
        has_links = cur.fetchone() is not None
    except sqlite3.Error:
        return {
            "events_total": 0,
            "accepted_total": 0,
            "acceptance_rate": None,
            "total_links": 0,
            "distinct_invoices_linked": 0,
            "avg_links_per_invoice": 0.0,
            "last_event_at": None,
            "last_link_at": None,
        }

    events_total = 0
    accepted_total = 0
    last_event_at = None
    # Build time filter conditionally (applied to ap_match_events)
    params: list[Any] = []
    clauses: list[str] = []
    if has_events and window_days > 0:
        clauses.append("julianday(created_at) >= julianday('now') - ?")
        params.append(window_days)
    window_where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    if has_events:
        events_total = int(_fetch_single_value(cur, f"SELECT COUNT(*) FROM ap_match_events{window_where}", tuple(params)) or 0)
        # accepted column may not exist (legacy). Guard via PRAGMA check.
        try:
            cur.execute("PRAGMA table_info(ap_match_events)")
            cols = {r[1] for r in cur.fetchall()}
            if "accepted" in cols:
                acc_clauses = list(clauses)  # copy
                acc_clauses.append("accepted=1")
                where_acc = (" WHERE " + " AND ".join(acc_clauses)) if acc_clauses else ""
                accepted_total = int(_fetch_single_value(cur, f"SELECT COUNT(*) FROM ap_match_events{where_acc}", tuple(params)) or 0)
            last_event_at = _fetch_single_value(cur, f"SELECT MAX(created_at) FROM ap_match_events{window_where}", tuple(params))
        except sqlite3.Error:
            pass

    total_links = 0
    distinct_invoices = 0
    last_link_at = None
    if has_links:
        try:
            link_clause = ""
            link_params: list[Any] = []
            if window_days > 0:
                link_clause = " WHERE julianday(created_at) >= julianday('now') - ?"
                link_params.append(window_days)
            total_links = int(_fetch_single_value(cur, f"SELECT COUNT(*) FROM ap_po_links{link_clause}", tuple(link_params)) or 0)
            distinct_invoices = int(_fetch_single_value(cur, f"SELECT COUNT(DISTINCT invoice_id) FROM ap_po_links{link_clause}", tuple(link_params)) or 0)
            last_link_at = _fetch_single_value(cur, f"SELECT MAX(created_at) FROM ap_po_links{link_clause}", tuple(link_params))
        except sqlite3.Error:
            pass

    acceptance_rate = None
    if events_total > 0:
        acceptance_rate = round(accepted_total / events_total, 4)
    avg_links = 0.0
    if distinct_invoices > 0:
        avg_links = round(total_links / distinct_invoices, 2)

    # Advanced metrics: candidate counts and confidence distribution (accepted vs rejected)
    candidates_avg = None
    confidence_acc_avg = None
    confidence_rej_avg = None
    confidence_p50 = None
    confidence_p95 = None
    confidence_sum = None  # exact sum across sampled events (up to limit)
    confidence_p99 = None
    confidence_high_ratio = None  # ratio of events with confidence >= 0.9
    confidence_stddev = None  # population std deviation across all confidences
    confidence_buckets: dict[str, int] = {}
    advanced_enabled = os.getenv("MATCHING_AP_ADVANCED", "1").lower() not in {"0", "false", "no", "off"}
    if has_events and events_total > 0 and advanced_enabled:
        try:
            # Fetch subset (limit 5000 to avoid heavy loads)
            cur.execute(
                f"SELECT candidates_json, confidence, accepted FROM ap_match_events{window_where} ORDER BY id DESC LIMIT 5000",
                tuple(params),
            )
            conf_all: list[float] = []
            conf_acc: list[float] = []
            conf_rej: list[float] = []
            cand_counts: list[int] = []
            # Use centralized bucket edges constant for confidence distribution
            from backend.recon_constants import AP_CONFIDENCE_BUCKET_EDGES as bucket_edges  # type: ignore
            bucket_counts = [0 for _ in bucket_edges]
            for cjson, conf, acc in cur.fetchall():
                # Parse candidates_json length (robust against malformed JSON / wrong types)
                try:
                    arr = json.loads(cjson or "[]")
                    cand_counts.append(len(arr) if isinstance(arr, list) else 0)
                except (json.JSONDecodeError, TypeError, ValueError):
                    cand_counts.append(0)
                # Normalize confidence to float
                try:
                    cf = float(conf or 0)
                except (TypeError, ValueError):
                    cf = 0.0
                conf_all.append(cf)
                if confidence_sum is None:
                    confidence_sum = cf
                else:
                    confidence_sum += cf
                if acc == 1:
                    conf_acc.append(cf)
                else:
                    conf_rej.append(cf)
                # bucket assignment (first edge >= cf)
                for i, edge in enumerate(bucket_edges):
                    if cf <= edge:
                        bucket_counts[i] += 1
                        break
            if cand_counts:
                candidates_avg = round(sum(cand_counts) / len(cand_counts), 2)
            if conf_acc:
                confidence_acc_avg = round(sum(conf_acc) / len(conf_acc), 4)
            if conf_rej:
                confidence_rej_avg = round(sum(conf_rej) / len(conf_rej), 4)
            if conf_all:
                try:
                    confidence_p50 = round(statistics.median(conf_all), 4)
                except statistics.StatisticsError:
                    confidence_p50 = None
                # Approximate p95 (list non-empty here, index safe)
                conf_sorted = sorted(conf_all)
                idx = int(0.95 * (len(conf_sorted) - 1))
                confidence_p95 = round(conf_sorted[idx], 4)
                # p99 (same method, positional)
                idx99 = int(0.99 * (len(conf_sorted) - 1))
                confidence_p99 = round(conf_sorted[idx99], 4)
                # High confidence ratio (>=0.9)
                try:
                    high_count = sum(1 for v in conf_all if v >= 0.9)
                    confidence_high_ratio = round(high_count / len(conf_all), 4)
                except Exception:  # noqa: BLE001 - defensive
                    confidence_high_ratio = None
                # Std deviation (population) for dispersion insight
                try:
                    if len(conf_all) > 1:
                        confidence_stddev = round(statistics.pstdev(conf_all), 4)
                    else:
                        confidence_stddev = 0.0 if conf_all else None
                except Exception:  # noqa: BLE001
                    confidence_stddev = None
            # Build bucket map labels scaled by 10000 (4 digits) without dot for deterministic sorting
            # Example: 0.20 becomes 02000 (0.2 * 10000=2000 -> 02000 with 5 width) producing label '00000_02000'
            prev_edge = 0.0
            scale = 10000
            for i, edge in enumerate(bucket_edges):
                left = int(round(prev_edge * scale))
                right = int(round(edge * scale))
                # Skip zero-width bucket (first iteration when prev_edge == edge == 0)
                if right == left:
                    prev_edge = edge
                    continue
                label = f"{left:05d}_{right:05d}"
                confidence_buckets[label] = bucket_counts[i]
                prev_edge = edge
        except sqlite3.Error:
            pass

    return {
        "events_total": events_total,
        "accepted_total": accepted_total,
        "acceptance_rate": acceptance_rate,
        "total_links": total_links,
        "distinct_invoices_linked": distinct_invoices,
        "avg_links_per_invoice": avg_links,
        "last_event_at": last_event_at,
        "last_link_at": last_link_at,
        "candidates_avg": candidates_avg,
        "confidence_acc_avg": confidence_acc_avg,
        "confidence_rej_avg": confidence_rej_avg,
        "confidence_p50": confidence_p50,
        "confidence_p95": confidence_p95,
        "confidence_p99": confidence_p99,
        "confidence_high_ratio": confidence_high_ratio,
        "confidence_stddev": confidence_stddev,
        "confidence_buckets": confidence_buckets or None,
        "confidence_sum": round(confidence_sum, 4) if confidence_sum is not None else None,
        "advanced_enabled": bool(advanced_enabled),
    }


def _ar_metrics(con: sqlite3.Connection, window_days: int, top: int) -> Dict[str, Any]:
    cur = con.cursor()
    try:
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ar_map_events'")
        has_events = cur.fetchone() is not None
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ar_project_rules'")
        has_rules = cur.fetchone() is not None
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sales_invoices'")
        has_invoices = cur.fetchone() is not None
    except sqlite3.Error:
        return {
            "events_total": 0,
            "rules_total": 0,
            "invoices_total": 0,
            "invoices_with_project": 0,
            "project_assign_rate": None,
            "last_event_at": None,
        }

    events_total = 0
    last_event_at = None
    ev_params: list[Any] = []
    ev_clauses: list[str] = []
    if has_events and window_days > 0:
        ev_clauses.append("julianday(created_at) >= julianday('now') - ?")
        ev_params.append(window_days)
    ev_where = (" WHERE " + " AND ".join(ev_clauses)) if ev_clauses else ""
    if has_events:
        try:
            events_total = int(_fetch_single_value(cur, f"SELECT COUNT(*) FROM ar_map_events{ev_where}", tuple(ev_params)) or 0)
            last_event_at = _fetch_single_value(cur, f"SELECT MAX(created_at) FROM ar_map_events{ev_where}", tuple(ev_params))
        except sqlite3.Error:
            pass
    rules_total = 0
    patterns_distinct = 0
    if has_rules:
        try:
            rules_total = int(_fetch_single_value(cur, "SELECT COUNT(*) FROM ar_project_rules") or 0)
            patterns_distinct = int(_fetch_single_value(cur, "SELECT COUNT(DISTINCT pattern) FROM ar_project_rules") or 0)
        except sqlite3.Error:
            pass
    invoices_total = 0
    invoices_with_project = 0
    if has_invoices:
        try:
            inv_params: list[Any] = []
            inv_clauses: list[str] = []
            if window_days > 0:
                inv_clauses.append("julianday(created_at) >= julianday('now') - ?")
                inv_params.append(window_days)
            inv_where = (" WHERE " + " AND ".join(inv_clauses)) if inv_clauses else ""
            invoices_total = int(_fetch_single_value(cur, f"SELECT COUNT(*) FROM sales_invoices{inv_where}", tuple(inv_params)) or 0)
            with_proj_where = inv_clauses + ["COALESCE(project_id,'')<>''"]
            with_proj_sql = f"SELECT COUNT(*) FROM sales_invoices WHERE {' AND '.join(with_proj_where)}" if with_proj_where else "SELECT COUNT(*) FROM sales_invoices WHERE COALESCE(project_id,'')<>''"
            invoices_with_project = int(_fetch_single_value(cur, with_proj_sql, tuple(inv_params)) or 0)
        except sqlite3.Error:
            pass
    project_assign_rate = None
    if invoices_total > 0:
        project_assign_rate = round(invoices_with_project / invoices_total, 4)

    # Top projects by invoice count (within window)
    top_projects: list[dict[str, Any]] = []
    if has_invoices and invoices_total > 0 and top > 0:
        try:
            params_tp: list[Any] = []
            tp_clauses: list[str] = ["COALESCE(project_id,'')<>''"]
            if window_days > 0:
                tp_clauses.insert(0, "julianday(created_at) >= julianday('now') - ?")
                params_tp.append(window_days)
            tp_where = " WHERE " + " AND ".join(tp_clauses)
            cur.execute(
                f"SELECT project_id, COUNT(*) as cnt FROM sales_invoices{tp_where} GROUP BY project_id ORDER BY cnt DESC LIMIT ?",
                (*params_tp, top),
            )
            rows = cur.fetchall()
            for pid, cnt in rows:
                share = round(cnt / invoices_total, 4) if invoices_total else 0
                top_projects.append({"project_id": pid, "count": cnt, "share": share})
        except sqlite3.Error:
            pass

    return {
        "events_total": events_total,
        "rules_total": rules_total,
        "invoices_total": invoices_total,
        "invoices_with_project": invoices_with_project,
        "project_assign_rate": project_assign_rate,
        "last_event_at": last_event_at,
        "patterns_distinct": patterns_distinct,
        "rules_project_coverage": round(patterns_distinct / rules_total, 4) if rules_total else None,
        "top_projects": top_projects or None,
    }


@matching_metrics_bp.get("/api/matching/metrics")
def matching_metrics_summary():  # pragma: no cover - exercised via tests
    started = datetime.now(UTC)
    window_days = 0
    top = 5
    try:
        window_days = max(0, int(request.args.get("window_days", "0")))
    except ValueError:
        window_days = 0
    try:
        top = max(0, min(50, int(request.args.get("top", "5"))))
    except ValueError:
        top = 5
    cache_key = (window_days, top)
    now_epoch = datetime.now(UTC).timestamp()
    cached = _CACHE.get(cache_key)
    if cached and (now_epoch - cached[0]) <= _CACHE_TTL_SECONDS:
        out = dict(cached[1])
        out["cache_hit"] = True
        return jsonify(out)
    with db_conn() as con:
        ap = _ap_metrics(con, window_days)
        ar = _ar_metrics(con, window_days, top)
    finished = datetime.now(UTC)
    out = {
        "generated_at": finished.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generation_ms": int((finished - started).total_seconds() * 1000),
        "window_days": window_days,
        "ap": ap,
        "ar": ar,
        "top": top,
    }
    _CACHE[cache_key] = (now_epoch, out)
    return jsonify(out)


@matching_metrics_bp.get("/api/matching/metrics/projects")
def matching_metrics_projects():  # pragma: no cover - new endpoint
    window_days = 0
    try:
        window_days = max(0, int(request.args.get("window_days", "0")))
    except ValueError:
        window_days = 0
    with db_conn() as con:
        cur = con.cursor()
        try:
            cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sales_invoices'")
            if not cur.fetchone():
                return jsonify({"items": [], "window_days": window_days})
            params: list[Any] = []
            proj_clauses: list[str] = []
            if window_days > 0:
                proj_clauses.append("julianday(created_at) >= julianday('now') - ?")
                params.append(window_days)
            total = _fetch_single_value(cur, f"SELECT COUNT(*) FROM sales_invoices{(' WHERE ' + ' AND '.join(proj_clauses)) if proj_clauses else ''}", tuple(params)) or 0
            proj_where_parts = list(proj_clauses)
            proj_where_parts.append("COALESCE(project_id,'')<>''")
            proj_where = " WHERE " + " AND ".join(proj_where_parts)
            cur.execute(
                f"SELECT project_id, COUNT(*) FROM sales_invoices{proj_where} GROUP BY project_id ORDER BY COUNT(*) DESC",
                tuple(params),
            )
            rows = cur.fetchall()
            items = []
            for pid, cnt in rows:
                share = round(cnt / total, 4) if total else 0
                items.append({"project_id": pid, "count": cnt, "share": share})
            return jsonify({"items": items, "total": total, "window_days": window_days})
        except sqlite3.Error:
            return jsonify({"items": [], "window_days": window_days})


@matching_metrics_bp.get("/api/matching/metrics/prom")
def matching_metrics_prom():  # pragma: no cover - lightweight exposition
    """Prometheus exposition for matching metrics (AP + AR).

    Mirrors the JSON summary but exports gauges with a stable naming scheme:

    matching_generation_ms
    matching_ap_events_total
    matching_ap_accepted_total
    matching_ap_acceptance_rate
    matching_ap_total_links
    matching_ap_distinct_invoices_linked
    matching_ap_avg_links_per_invoice
    matching_ap_candidates_avg
    matching_ap_confidence_p50 / _p95 / _acc_avg / _rej_avg
    matching_ar_events_total
    matching_ar_rules_total
    matching_ar_invoices_total
    matching_ar_invoices_with_project
    matching_ar_project_assign_rate
    matching_ar_patterns_distinct
    matching_ar_rules_project_coverage
    matching_ar_top_project_count{project_id="..."}
    matching_ar_top_project_share{project_id="..."}
    matching_cache_hit (0/1 for last query)
    """
    try:
        from prometheus_client import CollectorRegistry, Gauge, generate_latest, CONTENT_TYPE_LATEST  # type: ignore
    except Exception:
        return jsonify({"error": "prometheus_client not installed"}), 500

    # Parse params similar to summary endpoint
    try:
        window_days = max(0, int(request.args.get("window_days", "0")))
    except ValueError:
        window_days = 0
    try:
        top = max(0, min(50, int(request.args.get("top", "5"))))
    except ValueError:
        top = 5
    started = datetime.now(UTC)
    with db_conn() as con:
        ap = _ap_metrics(con, window_days)
        ar = _ar_metrics(con, window_days, top)
    generation_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
    reg = CollectorRegistry()

    def g(name: str, desc: str, value: float):
        try:
            Gauge(name, desc, registry=reg).set(float(value))
        except Exception:  # noqa: BLE001 - defensive gauge registration
            pass

    # AP gauges
    g("matching_generation_ms", "Time to generate metrics (ms)", generation_ms)
    g("matching_window_days", "Window days applied", window_days)
    g("matching_top", "Top N projects parameter", top)
    g("matching_ap_events_total", "Total AP match events", ap.get("events_total") or 0)
    g("matching_ap_accepted_total", "Accepted AP match events", ap.get("accepted_total") or 0)
    if ap.get("acceptance_rate") is not None:
        g("matching_ap_acceptance_rate", "AP acceptance rate", ap["acceptance_rate"])  # type: ignore[index]
    g("matching_ap_total_links", "Total PO links", ap.get("total_links") or 0)
    g("matching_ap_distinct_invoices_linked", "Distinct invoices with links", ap.get("distinct_invoices_linked") or 0)
    g("matching_ap_avg_links_per_invoice", "Average links per linked invoice", ap.get("avg_links_per_invoice") or 0.0)
    # Advanced AP stats
    for fld in [
        ("candidates_avg", "Average candidate list length"),
        ("confidence_acc_avg", "Average confidence accepted"),
        ("confidence_rej_avg", "Average confidence rejected"),
        ("confidence_p50", "Median confidence"),
        ("confidence_p95", "p95 confidence"),
        ("confidence_p99", "p99 confidence"),
        ("confidence_high_ratio", "Ratio of events with confidence >= 0.9"),
        ("confidence_stddev", "Std deviation of confidence values"),
    ]:
        val = ap.get(fld[0])
        if val is not None:
            g("matching_ap_" + fld[0], fld[1], val)
    # Confidence bucket gauges (expose each as matching_ap_confidence_bucket{range="0000_0200"})
    try:
        buckets = ap.get("confidence_buckets") or {}
        if buckets:
            from prometheus_client import Gauge as _Gauge  # type: ignore
            cb_g = _Gauge(
                "matching_ap_confidence_bucket",
                "Count of events by confidence bucket (le-style textual range)",
                ["range"],
                registry=reg,
            )
            for rng, cnt in buckets.items():
                cb_g.labels(range=rng).set(float(cnt))
            # Also export cumulative histogram style series: matching_ap_confidence_hist_bucket{le="..."}
            try:
                from prometheus_client import Gauge as _HG  # type: ignore
                hist_g = _HG(
                    "matching_ap_confidence_hist_bucket",
                    "Cumulative confidence distribution (Prometheus histogram style)",
                    ["le"],
                    registry=reg,
                )
                cumulative = 0
                # Derive numeric upper bound from label right side
                for rng, cnt in buckets.items():
                    right_raw = rng.split('_')[1]
                    try:
                        ub = float(int(right_raw) / 10000.0)
                    except (ValueError, TypeError):  # malformed label
                        ub = 0.0
                    cumulative += cnt
                    hist_g.labels(le=f"{ub:.4f}").set(float(cumulative))
                # +Inf bucket
                hist_g.labels(le="+Inf").set(float(cumulative))
                # Derive bucket-based percentiles (p95, p99) from cumulative buckets
                try:
                    total_bucket_events = sum(buckets.values())
                    if total_bucket_events > 0:
                        def _derive_bucket_percentile(p: float) -> float | None:
                            threshold = int(p * total_bucket_events)
                            running = 0
                            for rng, cnt in buckets.items():
                                running += cnt
                                if running >= threshold:
                                    right_raw = rng.split('_')[1]
                                    try:
                                        return int(right_raw) / 10000.0
                                    except Exception:  # noqa: BLE001
                                        return None
                            return None
                        p95_bucket_val = _derive_bucket_percentile(0.95)
                        if p95_bucket_val is not None:
                            g("matching_ap_confidence_p95_bucket", "Approximate p95 confidence from bucket upper bound", p95_bucket_val)
                        p99_bucket_val = _derive_bucket_percentile(0.99)
                        if p99_bucket_val is not None:
                            g("matching_ap_confidence_p99_bucket", "Approximate p99 confidence from bucket upper bound", p99_bucket_val)
                except Exception:  # noqa: BLE001 - percentile derivation optional
                    pass
                # Count & sum (exact if captured in advanced metrics, else midpoint approximation)
                total_events = ap.get("events_total") or 0
                exact_sum = ap.get("confidence_sum")
                if exact_sum is None:
                    s = 0.0
                    for rng, cnt in buckets.items():
                        left_raw, right_raw = rng.split('_')
                        try:
                            left_bound = int(left_raw) / 10000.0
                            r = int(right_raw) / 10000.0
                            mid = (left_bound + r) / 2.0
                        except (ValueError, TypeError):  # malformed label bounds
                            mid = 0.0
                        s += mid * cnt
                    exact_sum = round(s, 4)
                g("matching_ap_confidence_count", "Total events considered for confidence histogram", total_events)
                g("matching_ap_confidence_sum", "Exact (or approximated) sum of confidence values", round(exact_sum, 4))
            except Exception:  # noqa: BLE001 - histogram optional, any registration or calc error is non-fatal
                pass
    except Exception:  # noqa: BLE001 - optional confidence buckets
        pass

    # AR gauges
    g("matching_ar_events_total", "Total AR map events", ar.get("events_total") or 0)
    g("matching_ar_rules_total", "Total AR project rules", ar.get("rules_total") or 0)
    g("matching_ar_invoices_total", "Total invoices (window)", ar.get("invoices_total") or 0)
    g("matching_ar_invoices_with_project", "Invoices with project assigned", ar.get("invoices_with_project") or 0)
    if ar.get("project_assign_rate") is not None:
        g("matching_ar_project_assign_rate", "Invoice project assignment rate", ar["project_assign_rate"])  # type: ignore[index]
    g("matching_ar_patterns_distinct", "Distinct rule patterns", ar.get("patterns_distinct") or 0)
    if ar.get("rules_project_coverage") is not None:
        g("matching_ar_rules_project_coverage", "Distinct patterns / total rules", ar["rules_project_coverage"])  # type: ignore[index]

    # Top projects as labeled gauges
    top_projects = ar.get("top_projects") or []
    try:
        tp_count = Gauge(
            "matching_ar_top_project_count", "Top project invoice counts", ["project_id"], registry=reg
        )
        tp_share = Gauge(
            "matching_ar_top_project_share", "Top project invoice share", ["project_id"], registry=reg
        )
        for item in top_projects:
            pid = str(item.get("project_id"))
            cnt = float(item.get("count") or 0)
            share = float(item.get("share") or 0.0)
            tp_count.labels(project_id=pid).set(cnt)
            tp_share.labels(project_id=pid).set(share)
    except Exception:  # noqa: BLE001 - labeled top project gauges
        pass

    # Provide a cache_hit gauge relative to immediate repeated call (optional quick cache check)
    cache_key = (window_days, top)
    cache_hit = 0
    # Access internal cache; if present and fresh after this generation treat as hit on subsequent call
    cached = _CACHE.get(cache_key)
    if cached and (datetime.now(UTC).timestamp() - cached[0]) <= _CACHE_TTL_SECONDS:
        cache_hit = 1
    g("matching_cache_hit", "Was (would) cache hit for this param set?", cache_hit)

    output = generate_latest(reg)
    return current_app.response_class(output, mimetype=CONTENT_TYPE_LATEST)


@matching_metrics_bp.get("/api/matching/metrics/mini")
def matching_metrics_mini():  # pragma: no cover - thin convenience endpoint
    """Lightweight subset of matching metrics for high-frequency dashboards.

    Fields:
      generated_at, window_days (always 0 for now),
      ap: {confidence_p95, confidence_p99, confidence_high_ratio, confidence_stddev, acceptance_rate}
      ar: {project_assign_rate}
    """
    window_days = 0
    with db_conn() as con:
        ap = _ap_metrics(con, window_days)
        ar = _ar_metrics(con, window_days, top=0)
    out = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": window_days,
        "ap": {
            "confidence_p95": ap.get("confidence_p95"),
            "confidence_p99": ap.get("confidence_p99"),
            "confidence_high_ratio": ap.get("confidence_high_ratio"),
            "confidence_stddev": ap.get("confidence_stddev"),
            "acceptance_rate": ap.get("acceptance_rate"),
        },
        "ar": {
            "project_assign_rate": ar.get("project_assign_rate"),
        },
    }
    return jsonify(out)
