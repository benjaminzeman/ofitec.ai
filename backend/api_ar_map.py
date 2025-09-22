from __future__ import annotations

import json
import re
import sqlite3
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request


bp = Blueprint("ar_map", __name__)


def _db(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def _get_db_path() -> str:
    import os as _os
    from pathlib import Path as _Path

    raw = _os.getenv("DB_PATH")
    base = _Path(__file__).resolve().parent.parent
    if raw:
        p = _Path(raw)
        if not p.is_absolute():
            p = base / p
        try:
            return str(p.resolve())
        except OSError:
            pass
    return str((base / "data" / "chipax_data.db").resolve())


class Unprocessable(ValueError):
    def __init__(self, error: str, detail: str | None = None, **extra: Any):
        self.payload: Dict[str, Any] = {"error": error, "detail": detail}
        self.payload.update(extra)


@bp.errorhandler(Unprocessable)
def _unprocessable(e: Unprocessable):  # type: ignore[reportGeneralTypeIssues]
    return jsonify(e.payload), 422


def _col_exists(cur: sqlite3.Cursor, table: str, col: str) -> bool:
    try:
        cur.execute(f"PRAGMA table_info({table})")
        return any((r[1] == col) for r in cur.fetchall())
    except sqlite3.Error:
        return False


def _aggregate(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Aggregate by project_id: keep max confidence and union reasons
    by_pid: Dict[str, Dict[str, Any]] = {}
    for it in items:
        pid = str(it.get("project_id") or "")
        if not pid:
            continue
        reasons = it.get("reasons") or []
        if isinstance(reasons, str):
            reasons = [reasons]
        entry = by_pid.get(pid)
        if not entry:
            new = dict(it)
            new["reasons"] = list(dict.fromkeys(reasons))  # unique, ordered
            by_pid[pid] = new
        else:
            # merge reasons
            merged = list(
                dict.fromkeys((entry.get("reasons") or []) + reasons)
            )
            entry["reasons"] = merged
            # max confidence
            if float(it.get("confidence") or 0) > float(
                entry.get("confidence") or 0
            ):
                entry["confidence"] = it.get("confidence")
            # prefer known project_name if missing
            if not entry.get("project_name") and it.get("project_name"):
                entry["project_name"] = it.get("project_name")
    out = list(by_pid.values())
    # Backward compat: expose first reason also as 'reason'
    for o in out:
        rs = o.get("reasons") or []
        if rs:
            o["reason"] = rs[0]
    out.sort(key=lambda x: float(x.get("confidence") or 0), reverse=True)
    return out


def _gather_suggestions(
    con: sqlite3.Connection, body: Dict[str, Any]
) -> List[Dict[str, Any]]:
    inv = body.get("invoice") or {}
    cust_name = (inv.get("customer_name") or "").strip()
    cust_rut = (inv.get("customer_rut") or "").strip()
    invoice_number = (inv.get("invoice_number") or "").strip()
    drive_path = (
        body.get("drive_path") or inv.get("drive_path") or ""
    ).strip()
    project_hint = (body.get("project_hint") or "").strip()

    cur = con.cursor()
    items: List[Dict[str, Any]] = []

    # Ensure rules table exists (compat with previous schema)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ar_project_rules(
          id INTEGER PRIMARY KEY,
          kind TEXT,
          pattern TEXT NOT NULL,
          project_id TEXT NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          created_by TEXT
        );
        """
    )

    # 0) alias_regex rules (prefer this when available)
    rule_type_col = _col_exists(cur, "ar_project_rules", "rule_type")
    confidence_col = _col_exists(cur, "ar_project_rules", "confidence")
    if cust_name or invoice_number:
        haystack = f"{cust_name} {invoice_number}".strip()
        try:
            if rule_type_col:
                cur.execute(
                    "SELECT project_id, pattern, COALESCE(confidence, 0.88) "
                    "FROM ar_project_rules WHERE rule_type='alias_regex'"
                )
            else:
                cur.execute(
                    "SELECT project_id, pattern, ? FROM ar_project_rules "
                    "WHERE kind='customer_name_like'",
                    (0.88,),
                )
            for pid, pattern, conf in cur.fetchall():
                try:
                    if re.search(str(pattern or ""), haystack, re.I):
                        items.append(
                            {
                                "project_id": pid,
                                "confidence": float(
                                    conf if confidence_col else conf
                                ),
                                "reasons": [f"alias:'{pattern}'"],
                            }
                        )
                except re.error:
                    continue
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            pass

    # 1) drive_path rules
    if drive_path:
        try:
            if rule_type_col:
                cur.execute(
                    "SELECT project_id, pattern, COALESCE(confidence, 0.9) "
                    "FROM ar_project_rules WHERE rule_type='drive_path'"
                )
            else:
                cur.execute(
                    "SELECT project_id, pattern, ? FROM ar_project_rules "
                    "WHERE kind='drive_path_like'",
                    (0.9,),
                )
            for pid, pattern, conf in cur.fetchall():
                try:
                    if re.search(str(pattern or ""), drive_path, re.I) or (
                        pattern and drive_path.find(str(pattern)) >= 0
                    ):
                        items.append(
                            {
                                "project_id": pid,
                                "confidence": float(conf),
                                "reasons": [f"drive:'{pattern}'"],
                            }
                        )
                except re.error:
                    continue
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            pass

    # 2) Historical mapping by RUT
    if cust_rut:
        try:
            cur.execute(
                "SELECT project_id, COUNT(*) as cnt "
                "FROM sales_invoices WHERE customer_rut = ? "
                "AND project_id IS NOT NULL AND project_id != '' "
                "GROUP BY project_id ORDER BY cnt DESC LIMIT 3",
                (cust_rut,),
            )
            rows = cur.fetchall()
            total = sum(r[1] for r in rows) or 0
            for pid, cnt in rows:
                conf = min(0.85, max(0.4, (cnt / max(1, total))))
                items.append(
                    {
                        "project_id": pid,
                        "confidence": conf,
                        "reasons": ["history:customer_rut"],
                    }
                )
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            pass

    # 3) Canonicalization via recon_aliases -> map to known project
    if cust_name and not items:
        try:
            cur.execute(
                "SELECT DISTINCT canonical FROM recon_aliases "
                "WHERE ? LIKE '%' || alias || '%' LIMIT 3",
                (cust_name,),
            )
            canonicals = [r[0] for r in cur.fetchall()]
            for cn in canonicals:
                pid = None
                pname = None
                try:
                    cur.execute(
                        "SELECT zoho_project_id, zoho_project_name "
                        "FROM projects_analytic_map "
                        "WHERE zoho_project_name = ? LIMIT 1",
                        (cn,),
                    )
                    row = cur.fetchone()
                    if row:
                        pid, pname = row[0], row[1]
                except (sqlite3.OperationalError, sqlite3.DatabaseError):
                    pid = None
                if not pid:
                    try:
                        cur.execute(
                            (
                                "SELECT id, name FROM projects "
                                "WHERE name = ? LIMIT 1"
                            ),
                            (cn,),
                        )
                        row2 = cur.fetchone()
                        if row2:
                            pid, pname = row2[0], row2[1]
                    except (sqlite3.OperationalError, sqlite3.DatabaseError):
                        pid = None
                if pid:
                    items.append(
                        {
                            "project_id": pid,
                            "project_name": pname,
                            "confidence": 0.7,
                            "reasons": ["alias:canonical"],
                        }
                    )
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            pass

    # 4) Name contains (analytic map)
    if not items and cust_name:
        try:
            cur.execute(
                "SELECT DISTINCT zoho_project_id, zoho_project_name "
                "FROM projects_analytic_map "
                "WHERE ? LIKE '%' || zoho_project_name || '%' LIMIT 5",
                (cust_name,),
            )
            for pid, pname in cur.fetchall():
                items.append(
                    {
                        "project_id": pid,
                        "project_name": pname,
                        "confidence": 0.5,
                        "reasons": ["heuristic:name_contains"],
                    }
                )
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            pass

    # 5) EP ±2% (cashflow_planned)
    try:
        cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='cashflow_planned'"
        )
        if cur.fetchone():
            try:
                amt = float(inv.get("total_amount") or 0)
            except (TypeError, ValueError):
                amt = 0.0
            dt = inv.get("issue_date") or inv.get("fecha") or ""
            tol = max(1000.0, amt * 0.02)
            if amt > 0 and dt:
                cur.execute(
                    (
                        """
                        SELECT project_id, fecha, monto
                        FROM cashflow_planned
                        WHERE project_id IS NOT NULL
                          AND (category IN ('ventas','ar','ingresos','cobros')
                               OR COALESCE(category,'')='')
                          AND abs(COALESCE(monto,0) - ?) <= ?
                          AND julianday(fecha) BETWEEN julianday(?) - 31
                              AND julianday(?) + 31
                        LIMIT 5
                        """
                    ),
                    (amt, tol, dt, dt),
                )
                for pid, _f, _m in cur.fetchall():
                    items.append(
                        {
                            "project_id": pid,
                            "confidence": 0.6,
                            "reasons": ["ep:amount±2%"],
                        }
                    )
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        pass

    # 6) Reconciliation cross-checks
    try:
        cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='recon_links'"
        )
        if cur.fetchone() and inv.get("invoice_id"):
            inv_id = None
            try:
                raw_inv_id = inv.get("invoice_id")
                inv_id = int(raw_inv_id) if raw_inv_id is not None and str(raw_inv_id).isdigit() else None
            except (TypeError, ValueError):
                inv_id = None
            if inv_id is not None:
                cur.execute(
                    "SELECT DISTINCT reconciliation_id FROM recon_links "
                    "WHERE sales_invoice_id = ?",
                    (inv_id,),
                )
                rec_ids = [r[0] for r in cur.fetchall()]
                for rid in rec_ids:
                    cur.execute(
                        "SELECT purchase_invoice_id, expense_id FROM "
                        "recon_links WHERE reconciliation_id = ?",
                        (rid,),
                    )
                    for ap_id, ex_id in cur.fetchall():
                        if ap_id:
                            try:
                                cur.execute(
                                    "SELECT project_name FROM ap_invoices "
                                    "WHERE id = ?",
                                    (ap_id,),
                                )
                                r = cur.fetchone()
                                if r and (r[0] or "").strip():
                                    pname = (r[0] or "").strip()
                                    cur.execute(
                                        "SELECT zoho_project_id FROM "
                                        "projects_analytic_map WHERE "
                                        "zoho_project_name = ? LIMIT 1",
                                        (pname,),
                                    )
                                    r2 = cur.fetchone()
                                    pid = r2[0] if r2 else None
                                    if pid:
                                        items.append(
                                            {
                                                "project_id": pid,
                                                "confidence": 0.55,
                                                "reasons": [
                                                    "recon:co-linked ap"
                                                ],
                                            }
                                        )
                            except (
                                sqlite3.OperationalError,
                                sqlite3.DatabaseError,
                            ):
                                pass
                        if ex_id:
                            try:
                                cur.execute(
                                    (
                                        "SELECT proyecto FROM expenses "
                                        "WHERE id = ?"
                                    ),
                                    (ex_id,),
                                )
                                r3 = cur.fetchone()
                                if r3 and (r3[0] or "").strip():
                                    pname2 = (r3[0] or "").strip()
                                    cur.execute(
                                        "SELECT zoho_project_id FROM "
                                        "projects_analytic_map WHERE "
                                        "zoho_project_name = ? LIMIT 1",
                                        (pname2,),
                                    )
                                    r4 = cur.fetchone()
                                    pid2 = r4[0] if r4 else None
                                    if pid2:
                                        items.append(
                                            {
                                                "project_id": pid2,
                                                "confidence": 0.5,
                                                "reasons": [
                                                    "recon:co-linked expense"
                                                ],
                                            }
                                        )
                            except (
                                sqlite3.OperationalError,
                                sqlite3.DatabaseError,
                            ):
                                pass
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        pass

    # 7) Drive path contains known project name/slug
    if drive_path and not items:
        try:
            cur.execute(
                (
                    "SELECT zoho_project_id, zoho_project_name "
                    "FROM projects_analytic_map WHERE ? LIKE '%' || "
                    "zoho_project_name || '%' LIMIT 3"
                ),
                (drive_path,),
            )
            for pid, pname in cur.fetchall():
                items.append(
                    {
                        "project_id": pid,
                        "project_name": pname,
                        "confidence": 0.7,
                        "reasons": ["drive:path_contains_name"],
                    }
                )
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            pass
        if not items:
            try:
                cur.execute(
                    (
                        "SELECT id, name FROM projects "
                        "WHERE ("
                        "    (? LIKE '%' || COALESCE(slug,'') || '%' "
                        "     AND COALESCE(slug,'') <> '') "
                        " OR (? LIKE '%' || COALESCE(name,'') || '%' "
                        "     AND COALESCE(name,'') <> '') "
                        " OR (? LIKE '%' || COALESCE(analytic_code,'') || '%' "
                        "     AND COALESCE(analytic_code,'') <> '') "
                        ") LIMIT 3"
                    ),
                    (drive_path, drive_path, drive_path),
                )
                for pid, pname in cur.fetchall():
                    items.append(
                        {
                            "project_id": pid,
                            "project_name": pname,
                            "confidence": 0.65,
                            "reasons": ["drive:path_contains_project"],
                        }
                    )
            except (sqlite3.OperationalError, sqlite3.DatabaseError):
                pass

    # 8) If project_hint provided, boost it
    if project_hint:
        items.insert(
            0,
            {
                "project_id": project_hint,
                "confidence": 0.95,
                "reasons": ["hint"],
            },
        )

    return _aggregate(items)[:10]


def _ensure_alias_candidates(cur: sqlite3.Cursor):
    """Ensure auxiliary tables/columns for alias auto-learning exist.

    We maintain a lightweight candidate accumulator table. When a pattern
    (regex or literal) repeatedly succeeds (auto_assign) we promote it to a
    persistent rule.
    """
    # Candidate accumulator
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ar_rule_candidates(
          id INTEGER PRIMARY KEY,
          pattern TEXT NOT NULL,
          project_id TEXT NOT NULL,
          hits INTEGER DEFAULT 0,
          last_hit TEXT,
          promoted_at TEXT,
          UNIQUE(pattern, project_id)
        );
        """
    )
    # Try to extend rules table with optional columns (idempotent)
    try:
        cur.execute("PRAGMA table_info(ar_project_rules)")
        cols = {r[1] for r in cur.fetchall()}
        if "rule_type" not in cols:
            cur.execute("ALTER TABLE ar_project_rules ADD COLUMN rule_type TEXT")
        if "confidence" not in cols:
            cur.execute("ALTER TABLE ar_project_rules ADD COLUMN confidence REAL")
    except sqlite3.Error:
        pass


def _track_alias_candidate(cur: sqlite3.Cursor, pattern: str, project_id: str, threshold: int = 3) -> dict:
    """Increment hits for (pattern, project_id) and promote to rule when threshold reached.

    Returns a dict with tracking info.
    """
    if not pattern or not project_id:
        return {"skipped": True}
    _ensure_alias_candidates(cur)
    # Upsert style increment
    cur.execute(
        """
        INSERT INTO ar_rule_candidates(pattern, project_id, hits, last_hit)
        VALUES(?,?,1, datetime('now'))
        ON CONFLICT(pattern, project_id) DO UPDATE SET
          hits = hits + 1,
          last_hit = datetime('now')
        """,
        (pattern, project_id),
    )
    cur.execute(
        "SELECT id, hits, promoted_at FROM ar_rule_candidates WHERE pattern=? AND project_id=?",
        (pattern, project_id),
    )
    row = cur.fetchone()
    promoted = False
    if row and (row[1] or 0) >= threshold and not row[2]:
        # Promote: insert into ar_project_rules if not exists with alias_regex rule_type
        try:
            cur.execute(
                "SELECT 1 FROM ar_project_rules WHERE pattern=? AND project_id=? AND COALESCE(rule_type,'')='alias_regex' LIMIT 1",
                (pattern, project_id),
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO ar_project_rules(kind, pattern, project_id, created_by, rule_type, confidence) VALUES(?,?,?,?,?,?)",
                    ("customer_name_like", pattern, project_id, "auto", "alias_regex", 0.88),
                )
            cur.execute(
                "UPDATE ar_rule_candidates SET promoted_at = datetime('now') WHERE id = ?",
                (row[0],),
            )
            promoted = True
        except sqlite3.Error:
            promoted = False
    return {
        "pattern": pattern,
        "project_id": project_id,
        "hits": row[1] if row else 1,
        "promoted": promoted,
        "threshold": threshold,
    }


@bp.post("/api/ar-map/suggestions")
def api_ar_map_suggestions():
    body = request.get_json(force=True) or {}
    con = _db(_get_db_path())
    try:
        items = _gather_suggestions(con, body)
        return jsonify({"items": items})
    finally:
        con.close()


@bp.post("/api/ar-map/confirm")
def api_ar_map_confirm():
    body = request.get_json(force=True) or {}
    rules = body.get("rules") or []
    meta = body.get("metadata") or {}
    if not isinstance(rules, list) or not rules:
        raise Unprocessable("invalid_payload", "rules vacío")
    user = (meta.get("user_id") or "system").strip()

    con = _db(_get_db_path())
    try:
        cur = con.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS ar_project_rules(
              id INTEGER PRIMARY KEY,
              kind TEXT NOT NULL,
              pattern TEXT NOT NULL,
              project_id TEXT NOT NULL,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP,
              created_by TEXT
            );
            CREATE TABLE IF NOT EXISTS ar_map_events(
              id INTEGER PRIMARY KEY,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP,
              user_id TEXT,
              payload TEXT
            );
            """
        )
        _ensure_alias_candidates(cur)
        cur.execute(
            "INSERT INTO ar_map_events(user_id, payload) VALUES(?,?)",
            (user, json.dumps(body, ensure_ascii=False)),
        )
        for r in rules:
            if not isinstance(r, dict):
                continue
            kind = (r.get("kind") or "").strip() or "customer_name_like"
            pattern = (r.get("pattern") or "").strip()
            project_id = (r.get("project_id") or "").strip()
            if not pattern or not project_id:
                continue
            cur.execute(
                "INSERT INTO ar_project_rules(kind, pattern, project_id, created_by) VALUES(?,?,?,?)",
                (kind, pattern, project_id, user),
            )
            try:
                _track_alias_candidate(cur, pattern, project_id)
            except sqlite3.Error:
                pass
        assignment = body.get("assignment") or {}
        invoice_id = (
            assignment.get("invoice_id") if isinstance(assignment, dict) else None
        ) or body.get("invoice_id") or (body.get("invoice") or {}).get("invoice_id")
        assign_project_id = (
            (assignment.get("project_id") if isinstance(assignment, dict) else None)
            or (rules[0].get("project_id") if rules and isinstance(rules[0], dict) else None)
            or body.get("project_id")
        )
        updated_invoices = 0
        if invoice_id and assign_project_id:
            try:
                cur.execute(
                    "UPDATE sales_invoices SET project_id = ? WHERE id = ?",
                    (str(assign_project_id), int(invoice_id)),
                )
                updated_invoices = cur.rowcount or 0
            except sqlite3.Error:
                updated_invoices = 0
        con.commit()
        return jsonify({
            "ok": True,
            "saved_rules": len(rules),
            "updated_invoices": updated_invoices,
        }), 201
    finally:
        con.close()


@bp.post("/api/ar-map/auto_assign")
def api_ar_map_auto_assign():
    """
    Auto-assign project to a sales invoice when top suggestion is over
    a threshold.

    Body: { invoice:{...}, invoice_id?:int, threshold?:float (def 0.97),
            dry_run?:bool }
    """
    body = request.get_json(force=True) or {}
    threshold = float(body.get("threshold") or 0.97)
    dry_run = bool(body.get("dry_run") or False)

    con = _db(_get_db_path())
    try:
        items = _gather_suggestions(con, body)
        chosen = items[0] if items else None
        safe = False
        if chosen and float(chosen.get("confidence") or 0) >= threshold:
            if len(items) == 1:
                safe = True
            elif len(items) > 1:
                second = items[1]
                # Require a clear margin from the second candidate
                chosen_conf = float(chosen.get("confidence") or 0)
                second_conf = float(second.get("confidence") or 0)
                safe = (chosen_conf - second_conf) >= 0.05
        updated = 0
        if safe and not dry_run:
            # Try to update invoice.project_id if we have an id
            inv = body.get("invoice") or {}
            inv_id = body.get("invoice_id") or inv.get("invoice_id")
            try:
                inv_id_int = int(inv_id) if inv_id is not None else None
            except (TypeError, ValueError):
                inv_id_int = None
            if inv_id_int is not None:
                try:
                    cur = con.cursor()
                    if chosen is not None:
                        cur.execute(
                            (
                                "UPDATE sales_invoices SET project_id = ? "
                                "WHERE id = ?"
                            ),
                            (str(chosen.get("project_id")), inv_id_int),
                        )
                    updated = cur.rowcount or 0
                    # Log event
                    cur.executescript(
                        """
                        CREATE TABLE IF NOT EXISTS ar_map_events(
                          id INTEGER PRIMARY KEY,
                          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                          user_id TEXT,
                          payload TEXT
                        );
                        """
                    )
                    payload = {
                        "action": "auto_assign",
                        "body": body,
                        "chosen": chosen,
                    }
                    cur.execute(
                        (
                            "INSERT INTO ar_map_events(user_id, payload) "
                            "VALUES(?,?)"
                        ),
                        ("auto", json.dumps(payload, ensure_ascii=False)),
                    )
                    # Alias candidate tracking (if reason includes alias:'pattern')
                    try:
                        if chosen is None:
                            reasons = []
                        else:
                            reasons = chosen.get("reasons") or []
                        if isinstance(reasons, str):
                            reasons = [reasons]
                        alias_patterns = []
                        for rs in reasons:
                            m = re.match(r"alias:'([^']+)'", rs)
                            if m:
                                alias_patterns.append(m.group(1))
                        if alias_patterns and chosen is not None:
                            cur2 = con.cursor()
                            _ensure_alias_candidates(cur2)
                            for ap in alias_patterns:
                                try:
                                    _track_alias_candidate(cur2, ap, str(chosen.get("project_id")))
                                except sqlite3.Error:
                                    continue
                    except (sqlite3.Error, ValueError):
                        pass
                    con.commit()
                except sqlite3.Error:
                    updated = 0
        return jsonify({
            "ok": True,
            "auto_assigned": bool(safe and not dry_run and updated > 0),
            "dry_run": dry_run,
            "threshold": threshold,
            "chosen": chosen,
            "updated_invoices": updated,
        })
    finally:
        con.close()


@bp.get("/api/ar-map/alias_candidates")
def api_ar_map_alias_candidates():  # pragma: no cover - simple listing
    """List alias candidate patterns with hit counts and promotion state.

    Accepts optional query params:
      - min_hits (int): filter by minimum hits (default 1)
      - promoted (0/1): filter by promoted state
    """
    args = request.args
    min_hits = 1
    try:
        raw_min = args.get("min_hits")
        if raw_min is not None and str(raw_min).strip():
            min_hits = max(1, int(raw_min))
    except (TypeError, ValueError):
        min_hits = 1
    promoted_filter = args.get("promoted")
    con = _db(_get_db_path())
    try:
        cur = con.cursor()
        _ensure_alias_candidates(cur)
        sql = "SELECT pattern, project_id, hits, last_hit, promoted_at FROM ar_rule_candidates WHERE hits >= ?"
        params: List[Any] = [min_hits]
        if promoted_filter == "1":
            sql += " AND promoted_at IS NOT NULL"
        elif promoted_filter == "0":
            sql += " AND promoted_at IS NULL"
        sql += " ORDER BY hits DESC, last_hit DESC LIMIT 200"
        try:
            cur.execute(sql, params)
            rows = cur.fetchall()
        except sqlite3.Error:
            rows = []
        out = [
            {
                "pattern": r[0],
                "project_id": r[1],
                "hits": r[2],
                "last_hit": r[3],
                "promoted_at": r[4],
            }
            for r in rows
        ]
        return jsonify({"items": out, "count": len(out)})
    finally:
        con.close()


@bp.get("/api/ar/rules_stats")
def api_ar_rules_stats():  # pragma: no cover
    """Lightweight AR rules & coverage stats (JSON).

    Mirrors core logic of tools/ar_rules_stats.py without importing it to
    avoid heavy startup cost. Returns 0 / null values if tables missing.
    """
    import os
    from datetime import datetime, timedelta

    db_path = os.environ.get("DB_PATH") or os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chipax_data.db")
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(db_path)
    if not os.path.exists(db_path):
        return jsonify({"error": "db_not_found", "db_path": db_path}), 200
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    def safe(sql: str, params=()):
        try:
            cur.execute(sql, params)
            return cur.fetchall()
        except sqlite3.Error:
            return []

    out = {}
    rows = safe("SELECT kind, COUNT(1) FROM ar_project_rules GROUP BY kind")
    rules_by_kind = {k: int(c) for k, c in rows}
    out["rules_by_kind"] = rules_by_kind
    out["rules_total"] = sum(rules_by_kind.values())
    rows = safe("SELECT COUNT(1) FROM sales_invoices")
    invoices_total = int(rows[0][0]) if rows else 0
    out["invoices_total"] = invoices_total
    rows = safe("SELECT COUNT(1) FROM sales_invoices WHERE TRIM(COALESCE(project_id,''))<>''")
    invoices_with_project = int(rows[0][0]) if rows else 0
    out["invoices_with_project"] = invoices_with_project
    out["project_assign_rate"] = round(invoices_with_project / invoices_total, 4) if invoices_total else None
    rows = safe("SELECT COUNT(DISTINCT TRIM(COALESCE(customer_name,''))) FROM sales_invoices WHERE TRIM(COALESCE(customer_name,''))<>''")
    distinct_names = int(rows[0][0]) if rows else 0
    out["distinct_customer_names"] = distinct_names
    rows = safe("""
        SELECT COUNT(DISTINCT si.customer_name)
          FROM sales_invoices si
          JOIN ar_project_rules r
            ON r.kind='customer_name_like' AND r.pattern=si.customer_name
         WHERE TRIM(COALESCE(si.customer_name,''))<>'')
    """)
    covered_names = int(rows[0][0]) if rows else 0
    out["customer_names_with_rule"] = covered_names
    out["customer_name_rule_coverage"] = round(covered_names / distinct_names, 4) if distinct_names else None
    cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat(timespec="seconds")
    rows = safe("SELECT COUNT(1) FROM ar_map_events WHERE created_at >= ?", (cutoff,))
    out["recent_events_30d"] = int(rows[0][0]) if rows else 0
    out["generated_at"] = datetime.utcnow().isoformat() + "Z"
    conn.close()
    return jsonify(out)
