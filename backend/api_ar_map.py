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
                inv_id = int(inv.get("invoice_id"))
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
        # Persist audit event
        cur.execute(
            "INSERT INTO ar_map_events(user_id, payload) VALUES(?,?)",
            (user, json.dumps(body, ensure_ascii=False)),
        )
        # Upsert simple rules set
        for r in rules:
            kind = (r.get("kind") or "").strip() or "customer_name_like"
            pattern = (r.get("pattern") or "").strip()
            project_id = (r.get("project_id") or "").strip()
            if not pattern or not project_id:
                continue
            cur.execute(
                "INSERT INTO ar_project_rules("
                "kind, pattern, project_id, created_by) VALUES(?,?,?,?)",
                (kind, pattern, project_id, user),
            )

        # Optional: assign project to a specific sales invoice
        assignment = body.get("assignment") or {}
        invoice_id = (
            assignment.get("invoice_id")
            if isinstance(assignment, dict)
            else None
        ) or body.get("invoice_id") or (
            body.get("invoice") or {}
        ).get("invoice_id")
        assign_project_id = (
            (
                assignment.get("project_id")
                if isinstance(assignment, dict)
                else None
            )
            or (
                rules[0].get("project_id")
                if rules and isinstance(rules[0], dict)
                else None
            )
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
                # Silently ignore if table/columns are missing; event still
                # captured
                updated_invoices = 0
        con.commit()
        return jsonify(
            {
                "ok": True,
                "saved_rules": len(rules),
                "updated_invoices": updated_invoices,
            }
        ), 201
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
