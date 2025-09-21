#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AP↔PO Matching API (v2 – diseño ideas/matching)

Endpoints:
    POST /api/ap-match/suggestions -> candidatos (Top-N) para una factura
    POST /api/ap-match/preview     -> valida reglas duras (3-way simplificado)
    POST /api/ap-match/confirm      -> persiste enlaces + evento de aprendizaje

Compatibilidad retro (tests existentes):
                                - Payload antiguo {"invoice": {rut, monto}} ->
                                    forma simple.
                                - Nuevo: vendor_id|vendor_rut, amount, date,
                                    invoice_id, project_id
                            opcional, amount_tol (0.02), days (30).

Implementación mínima viable del diseño:
    - Tablas: ap_po_links (N-M) y ap_match_events (bitácora) ampliadas.
    - Saldos por línea si existen vistas; sino, cae a nivel cabecera.
    - Greedy subset-sum para aproximar monto dentro de tolerancia.
    - Validaciones: over_allocation, vendor mismatch (básica) progresiva.
    - Explicabilidad: reasons[] con heurísticas aplicadas.

Limitaciones iniciales (pendientes para iteraciones futuras):
    - No incluye aún similitud de descripciones ni GRN avanzadas.
    - 3-way profundo depende de vistas potencialmente ausentes.
    - Split/Merge multi-PO avanzado pendiente.
"""
from __future__ import annotations
# pylint: disable=too-many-locals,too-many-branches,too-many-statements

import json
import os
import sqlite3
from math import exp
from pathlib import Path
from typing import Any

from flask import Blueprint, jsonify, request

from backend.db_utils import db_conn

bp = Blueprint("ap_match", __name__)


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
_raw_db = os.getenv("DB_PATH")
if _raw_db:
    _p = Path(_raw_db)
    if not _p.is_absolute():
        _p = PROJECT_ROOT / _p
    DB_PATH = str(_p.resolve())
else:
    DB_PATH = str((PROJECT_ROOT / "data" / "chipax_data.db").resolve())


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master"
        " WHERE type IN ('table','view') AND name=?",
        (name,),
    )
    return cur.fetchone() is not None


def _ensure_tables(conn: sqlite3.Connection) -> None:
    """Create core tables if missing (idempotent)."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ap_po_links (
          id INTEGER PRIMARY KEY,
          invoice_id INTEGER NOT NULL,
          invoice_line_id INTEGER,
          po_id TEXT,
          po_line_id TEXT,
          amount REAL NOT NULL,
          qty REAL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          created_by TEXT
        );
                CREATE INDEX IF NOT EXISTS idx_ap_po_links_inv
                    ON ap_po_links(invoice_id);
                CREATE INDEX IF NOT EXISTS idx_ap_po_links_pol
                    ON ap_po_links(po_line_id);
        CREATE TABLE IF NOT EXISTS ap_match_events (
          id INTEGER PRIMARY KEY,
          invoice_id INTEGER NOT NULL,
          source_json TEXT NOT NULL,
          candidates_json TEXT NOT NULL,
          chosen_json TEXT,
          confidence REAL,
          reasons TEXT,
          accepted INTEGER,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          user_id TEXT
        );
                -- Tolerance / config precedence: vendor > project > global
                                CREATE TABLE IF NOT EXISTS ap_match_config (
                                    id INTEGER PRIMARY KEY,
                                    scope_type TEXT NOT NULL,  -- g|v|p
                                    scope_value TEXT,          -- NULL global
                                    amount_tol_pct REAL,       -- 0.02=2%
                                    qty_tol_pct REAL,          -- 0.05=5%
                                    recv_required INTEGER DEFAULT 0,
                                    weight_vendor REAL,
                                    weight_amount REAL,
                                    weight_3way REAL,
                                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                                );
                CREATE INDEX IF NOT EXISTS idx_ap_match_config_scope
                        ON ap_match_config(scope_type, scope_value);
        """
    )
    _migrate_legacy_ap_po_links(conn)
    _ensure_events_table(conn)


def _migrate_legacy_ap_po_links(conn: sqlite3.Connection) -> None:
    """Migrate legacy ap_po_links shape if present.

    Legacy columns: ap_invoice_id, line_id, user_id.
    Target columns: invoice_id, invoice_line_id, po_line_id, created_by.
    """
    try:  # pragma: no cover - defensive
        cur = conn.execute("PRAGMA table_info(ap_po_links)")
        cols = [r[1] for r in cur.fetchall()]
        if not cols:
            return
        if "ap_invoice_id" in cols and "invoice_id" not in cols:
            # Rename legacy table
            conn.execute(
                "ALTER TABLE ap_po_links RENAME TO ap_po_links_legacy"
            )
            # Recreate new table (same DDL as in _ensure_tables)
            conn.executescript(
                """
                CREATE TABLE ap_po_links (
                  id INTEGER PRIMARY KEY,
                  invoice_id INTEGER NOT NULL,
                  invoice_line_id INTEGER,
                  po_id TEXT,
                  po_line_id TEXT,
                  amount REAL NOT NULL,
                  qty REAL,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                  created_by TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_ap_po_links_inv
                    ON ap_po_links(invoice_id);
                CREATE INDEX IF NOT EXISTS idx_ap_po_links_pol
                    ON ap_po_links(po_line_id);
                """
            )
            # Copy data mapping columns; preserve created_at if present
            legacy_cols = list(cols)
            has_created_at = "created_at" in legacy_cols
            if has_created_at:
                insert_sql = (
                    "INSERT INTO ap_po_links("  # legacy copy with dates
                    "invoice_id, po_id, po_line_id, amount, created_by, "
                    "created_at) SELECT ap_invoice_id, po_id, line_id, "
                    "amount, user_id, created_at FROM ap_po_links_legacy"
                )
            else:
                insert_sql = (
                    "INSERT INTO ap_po_links("  # fallback no created_at
                    "invoice_id, po_id, po_line_id, amount, created_by) "
                    "SELECT ap_invoice_id, po_id, line_id, amount, user_id "
                    "FROM ap_po_links_legacy"
                )
            conn.execute(insert_sql)
            # Keep legacy for audit or drop; we keep to avoid destructive loss
    except sqlite3.Error:
        pass


def _ensure_events_table(conn: sqlite3.Connection) -> None:
    """If only legacy ap_match_events(payload) exists create new table."""
    try:  # pragma: no cover
        cur = conn.execute("PRAGMA table_info(ap_match_events)")
        cols = [r[1] for r in cur.fetchall()]
        if not cols:
            return
        # Legacy shape: id, created_at, user_id, payload
        if "payload" in cols and "invoice_id" not in cols:
            # Create new table if not exists under different name
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS ap_match_events_new (
                  id INTEGER PRIMARY KEY,
                  invoice_id INTEGER NOT NULL,
                  source_json TEXT NOT NULL,
                  candidates_json TEXT NOT NULL,
                  chosen_json TEXT,
                  confidence REAL,
                  reasons TEXT,
                  accepted INTEGER,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                  user_id TEXT
                );
                """
            )
            # We do not auto-migrate opaque payload; leave legacy table intact.
    except sqlite3.Error:
        pass


def _fetch_po_headers(
    conn: sqlite3.Connection,
    vendor_rut: str | None,
    date: str | None,
    days: int,
) -> list[dict[str, Any]]:
    """Fetch PO headers within date window and (optionally) vendor."""
    if not _table_exists(conn, "purchase_orders_unified"):
        return []
    where = ["1=1"]
    params: list[Any] = []
    if vendor_rut:
        where.append("COALESCE(vendor_rut,'') = ?")
        params.append(vendor_rut)
    if date:
        where.append(
            "date(po_date) BETWEEN date(?,'-" + str(days) + " day') "
            "AND date(?,'+" + str(days) + " day')"
        )
        params.extend([date, date])
    sql = (
        "SELECT id, po_number, po_date, vendor_rut, "
        "COALESCE(total_amount,0) AS total_amount, "
        "COALESCE(currency,'CLP') AS currency, "
        "COALESCE(status,'unknown') AS status "
        "FROM purchase_orders_unified WHERE " + " AND ".join(where)
    )
    cur = conn.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def _score_header(
    po: dict[str, Any],
    amount: float | None,
    vendor_rut: str | None,
) -> tuple[float, list[str]]:
    score = 0.4
    reasons: list[str] = []
    if vendor_rut and po.get("vendor_rut") == vendor_rut:
        score += 0.2
        reasons.append("same_vendor")
    if amount is not None:
        po_total = float(po.get("total_amount") or 0)
        if po_total <= 0:
            pass
        else:
            delta_pct = abs(po_total - amount) / max(amount, 1e-6)
            # amount contribution (exponential decay)
            amount_score = exp(-4 * delta_pct)
            reasons.append(f"amount_delta_pct={delta_pct:.3f}")
            score += 0.3 * amount_score
            if delta_pct < 0.0005:
                reasons.append("exact_amount")
            elif delta_pct < 0.01:
                reasons.append("amount_within_1pct")
    return (round(min(score, 0.99), 3), reasons)


def _subset_greedy(
    rows: list[dict[str, Any]],
    target: float,
    tol: float,
) -> tuple[list[dict[str, Any]], float]:
    """Greedy pick descending amounts until within tolerance or cannot improve.
    Returns (picked_rows, accumulated_amount)."""
    if target <= 0:
        return [], 0.0
    lower, upper = target * (1 - tol), target * (1 + tol)
    ordered = sorted(
        rows,
        key=lambda r: float(
            r.get("amt_remaining") or r.get("total_amount") or 0
        ),
        reverse=True,
    )
    acc = 0.0
    picked: list[dict[str, Any]] = []
    for r in ordered:
        amt = float(r.get("amt_remaining") or r.get("total_amount") or 0)
        if amt <= 0:
            continue
        if acc + amt <= upper:
            picked.append(r)
            acc += amt
        if acc >= lower:
            break
    if acc < lower:  # fail to reach tolerance
        return [], 0.0
    return picked, acc


def _load_tolerances(
    conn: sqlite3.Connection,
    vendor_rut: str | None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Resolve tolerance config with precedence vendor > project > global.

    Returns dict with keys: amount_tol_pct, qty_tol_pct, recv_required,
    source_layers
    """
    base = {"amount_tol_pct": 0.02, "qty_tol_pct": 0.0, "recv_required": 0}
    if not _table_exists(conn, "ap_match_config"):
        return {**base, "source_layers": ["defaults"]}
    layers: list[str] = ["defaults"]
    cur = conn.execute(
        "SELECT amount_tol_pct, qty_tol_pct, recv_required "
        "FROM ap_match_config WHERE scope_type='global' "
        "ORDER BY id DESC LIMIT 1"
    )
    row = cur.fetchone()
    if row:
        for k in ("amount_tol_pct", "qty_tol_pct", "recv_required"):
            if row[k] is not None:
                base[k] = row[k]
        layers.append("global")
    if project_id:
        cur = conn.execute(
            "SELECT amount_tol_pct, qty_tol_pct, recv_required "
            "FROM ap_match_config WHERE scope_type='project' "
            "AND scope_value=? ORDER BY id DESC LIMIT 1",
            (str(project_id),),
        )
        prow = cur.fetchone()
        if prow:
            for k in ("amount_tol_pct", "qty_tol_pct", "recv_required"):
                if prow[k] is not None:
                    base[k] = prow[k]
            layers.append("project")
    if vendor_rut:
        cur = conn.execute(
            "SELECT amount_tol_pct, qty_tol_pct, recv_required "
            "FROM ap_match_config WHERE scope_type='vendor' "
            "AND scope_value=? ORDER BY id DESC LIMIT 1",
            (vendor_rut,),
        )
        vrow = cur.fetchone()
        if vrow:
            for k in ("amount_tol_pct", "qty_tol_pct", "recv_required"):
                if vrow[k] is not None:
                    base[k] = vrow[k]
            layers.append("vendor")
    base["source_layers"] = layers
    return base


@bp.route("/api/ap-match/suggestions", methods=["POST"])
def ap_match_suggestions():
    """Return AP match candidates applying layered config precedence."""
    data = request.get_json(silent=True) or {}

    # Backward compatibility (existing tests send {invoice:{...}})
    legacy_inv = data.get("invoice") or {}
    vendor_rut = (
        data.get("vendor_rut")
        or legacy_inv.get("vendor_rut")
        or ""
    ).strip() or None
    amount = data.get("amount") or legacy_inv.get("amount")
    date = (data.get("date") or legacy_inv.get("date") or "").strip() or None
    invoice_id = (
        data.get("invoice_id")
        or legacy_inv.get("id")
        or legacy_inv.get("invoice_id")
    )
    # UI may still send amount_tol override; else use config precedence
    amount_tol_override = data.get("amount_tol")
    days = int(data.get("days", 30) or 30)
    project_id = data.get("project_id") or legacy_inv.get("project_id")

    suggestions: list[dict[str, Any]] = []
    try:
        with db_conn() as conn:
            headers = _fetch_po_headers(conn, vendor_rut, date, days)

            # Load tolerances (line-level amount tolerance for greedy subset)
            tol_cfg = _load_tolerances(conn, vendor_rut, project_id)
            amount_tol = (
                float(amount_tol_override)
                if amount_tol_override is not None
                else float(tol_cfg.get("amount_tol_pct", 0.02) or 0.02)
            )
            if not headers:
                return jsonify({"items": suggestions})

            # Vista de saldos por línea si existe; de lo contrario cabecera
            line_rows: list[dict[str, Any]] = []
            if _table_exists(conn, "v_po_line_balances_pg"):
                cur = conn.execute(
                    "SELECT po_line_id, po_id, qty_remaining, amt_remaining "
                    "FROM v_po_line_balances_pg WHERE amt_remaining > 0"
                )
                line_rows = [dict(r) for r in cur.fetchall()]

            picked_lines: list[dict[str, Any]] = []
            acc_amt = 0.0
            if amount is not None and line_rows:
                picked_lines, acc_amt = _subset_greedy(
                    line_rows, float(amount), amount_tol
                )

            if picked_lines:
                po_ids = list({r["po_id"] for r in picked_lines})
                coverage_pct = acc_amt / float(amount) if amount else 0
                confidence_base = 0.6 + min(0.35, coverage_pct * 0.35)
                reasons = [f"coverage_pct={coverage_pct:.3f}"]
                reasons.append(
                    "amount_tol_used="
                    f"{amount_tol:.4f}/sources="
                    f"{','.join(tol_cfg['source_layers'])}"
                )
                suggestions.append(
                    {
                        "candidate": {
                            "po_id": po_ids,
                            "lines": [
                                {
                                    "po_line_id": r["po_line_id"],
                                    "qty_avail": r.get("qty_remaining"),
                                    "unit_price": None,
                                }
                                for r in picked_lines
                            ],
                            "coverage": {
                                "amount": round(acc_amt, 2),
                                "pct": round(coverage_pct, 4),
                            },
                        },
                        "confidence": round(min(confidence_base, 0.99), 3),
                        "reasons": reasons,
                    }
                )

            # Incluir también sugerencias por cabecera (compatibilidad) Top-5
            for po in headers[:5]:
                header_conf, header_reasons = _score_header(
                    po,
                    float(amount) if amount is not None else None,
                    vendor_rut,
                )
                header_reasons.append(
                    "amount_tol_used="
                    f"{amount_tol:.4f}/sources="
                    f"{','.join(tol_cfg['source_layers'])}"
                )
                suggestions.append(
                    {
                        # legacy fields para tests existentes
                        "po_id": po.get("id"),
                        "po_number": po.get("po_number"),
                        "po_date": po.get("po_date"),
                        "vendor_rut": po.get("vendor_rut"),
                        "total_amount": po.get("total_amount"),
                        "currency": po.get("currency"),
                        "status": po.get("status"),
                        "confidence": header_conf,
                        "reasons": header_reasons,
                    }
                )
    except sqlite3.Error:
        suggestions = []

    return jsonify({"items": suggestions, "invoice_id": invoice_id})


@bp.route("/api/ap-match/preview", methods=["POST"])
def ap_match_preview():
    """Validate a suggested PO selection and surface blocking errors."""
    data = request.get_json(silent=True) or {}
    invoice_id = data.get("invoice_id")
    links = data.get("links") or []
    vendor_rut = data.get("vendor_rut")
    project_id = data.get("project_id")
    if not links:
        return jsonify({"error": "links_required"}), 422

    # Aggregate amounts per PO for over-allocation check
    per_po: dict[str, float] = {}
    for link in links:
        po_id = (
            str(link.get("po_id")) if link.get("po_id") is not None else None
        )
        if not po_id:
            return jsonify({
                "error": "invalid_link",
                "detail": "po_id missing",
            }), 422
        amt = float(link.get("amount") or 0)
        per_po[po_id] = per_po.get(po_id, 0.0) + amt

    violations: list[dict[str, Any]] = []
    line_summaries: list[dict[str, Any]] = []
    tol_used: dict[str, Any] = {}
    try:
        with db_conn() as conn:
            # Ensure core tables so feedback route won't fail later
            _ensure_tables(conn)
            tol_used = _load_tolerances(conn, vendor_rut, project_id)
            amount_tol_cfg = float(
                tol_used.get("amount_tol_pct", 0.02) or 0.02
            )
            qty_tol_cfg = float(tol_used.get("qty_tol_pct", 0.0) or 0.0)
            recv_required = int(tol_used.get("recv_required", 0) or 0)

            if _table_exists(conn, "purchase_orders_unified"):
                cur = conn.execute(
                    "SELECT id, COALESCE(total_amount,0) AS total_amount "
                    "FROM purchase_orders_unified"
                )
                totals = {str(r[0]): float(r[1] or 0) for r in cur.fetchall()}
                for po_id, used in per_po.items():
                    po_total = totals.get(po_id)
                    if po_total is not None and used > po_total + 1e-6:
                        violations.append(
                            {
                                "po_id": po_id,
                                "used": round(used, 2),
                                "po_total": round(po_total, 2),
                                "reason": "links_exceed_po_total",
                            }
                        )

            # Per-line validations (3-way lite) if po_line_id present
            has_balances = _table_exists(conn, "v_po_line_balances_pg")
            has_3way = _table_exists(conn, "v_3way_status_po_line_ext_pg")
            balances: dict[str, Any] = {}
            threeway: dict[str, sqlite3.Row] = {}
            if has_balances:
                bal_cur = None
                try:
                    bal_cur = conn.execute(
                        "SELECT po_line_id, qty_remaining, amt_remaining, "
                        "qty_invoiced, qty_received, po_id "
                        "FROM v_po_line_balances_pg"
                    )
                except sqlite3.Error:
                    # Fallback minimal shape (test env) without extra cols
                    try:
                        bal_cur = conn.execute(
                            "SELECT po_line_id, po_id, qty_remaining, "
                            "amt_remaining FROM v_po_line_balances_pg"
                        )
                    except sqlite3.Error:
                        bal_cur = None
                if bal_cur is not None:
                    for r in bal_cur.fetchall():
                        # Normalize into dict with expected keys
                        if len(r.keys()) == 6:  # full shape
                            balances[str(r[0])] = r
                        else:  # minimal shape map positions
                            balances[str(r[0])] = {
                                "po_line_id": r[0],
                                "po_id": r[1],
                                "qty_remaining": r[2],
                                "amt_remaining": r[3],
                                "qty_invoiced": None,
                                "qty_received": None,
                            }
            if has_3way:
                cur = conn.execute(
                    "SELECT po_line_id, recv_qty, inv_qty, po_qty "
                    "FROM v_3way_status_po_line_ext_pg"
                )
                for r in cur.fetchall():
                    threeway[str(r[0])] = r

            for link in links:
                po_line_id = link.get("po_line_id")
                amt = float(link.get("amount") or 0)
                qty = link.get("qty")
                summary = {"po_line_id": po_line_id, "amount": amt, "qty": qty}
                if not po_line_id:
                    line_summaries.append(summary)
                    continue
                bal = balances.get(str(po_line_id))
                if bal:
                    qty_remaining = float(bal["qty_remaining"] or 0)
                    amt_remaining = float(bal["amt_remaining"] or 0)
                    summary.update({
                        "qty_remaining": qty_remaining,
                        "amt_remaining": amt_remaining,
                    })
                    if qty is not None and qty_remaining >= 0:
                        if qty > qty_remaining * (1 + qty_tol_cfg) + 1e-9:
                            violations.append({
                                "po_line_id": po_line_id,
                                "reason": "qty_exceeds_remaining",
                                "qty": qty,
                                "qty_remaining": qty_remaining,
                                "qty_tol_pct": qty_tol_cfg,
                            })
                    if (
                        amt_remaining >= 0
                        and amt > amt_remaining * (1 + amount_tol_cfg) + 1e-9
                    ):
                        violations.append({
                            "po_line_id": po_line_id,
                            "reason": "amount_exceeds_remaining",
                            "amount": amt,
                            "amt_remaining": amt_remaining,
                            "amount_tol_pct": amount_tol_cfg,
                        })
                tw = threeway.get(str(po_line_id))
                if recv_required and tw and qty is not None:
                    recv_qty = float(tw["recv_qty"] or 0)
                    inv_qty = float(tw["inv_qty"] or 0)
                    po_qty = float(tw["po_qty"] or 0)
                    inv_after = inv_qty + qty
                    summary.update({
                        "recv_qty": recv_qty,
                        "current_inv_qty": inv_qty,
                        "po_qty": po_qty,
                        "inv_qty_after": inv_after,
                    })
                    if inv_after > recv_qty * (1 + qty_tol_cfg) + 1e-9:
                        violations.append({
                            "po_line_id": po_line_id,
                            "reason": "invoice_over_receipt",
                            "invoice_qty_after": inv_after,
                            "recv_qty": recv_qty,
                            "qty_tol_pct": qty_tol_cfg,
                        })
                line_summaries.append(summary)
    except sqlite3.Error:  # pragma: no cover - fallback silencioso
        pass

    return jsonify({
        "ok": len(violations) == 0,
        "invoice_id": invoice_id,
        "violations": violations,
        "deltas": {"by_po": per_po},
        "tolerances": tol_used,
        "lines": line_summaries,
    })


@bp.route("/api/ap-match/feedback", methods=["POST"])
def ap_match_feedback():
    """Registra feedback de aceptación / rechazo para un matching generado.

    Body JSON: { invoice_id, accepted: 0|1, reason?, user_id? }
    Crea un evento en ap_match_events si tabla moderna existe.
    Responde siempre 200 salvo payload inválido.
    """
    data = request.get_json(silent=True) or {}
    invoice_id = data.get("invoice_id") or data.get("ap_invoice_id")
    if not invoice_id:
        return jsonify({"error": "invoice_id_required"}), 422
    accepted = int(1 if data.get("accepted") in (1, True, "1", "true") else 0)
    reason = (data.get("reason") or "").strip() or None
    user_id = (data.get("user_id") or data.get("user") or "system").strip()
    try:
        with db_conn() as conn:
            _ensure_tables(conn)
            cur = conn.cursor()
            # Detect modern events table
            ev_cols = [
                r[1]
                for r in cur.execute(
                    "PRAGMA table_info(ap_match_events)"
                ).fetchall()
            ]
            if "invoice_id" in ev_cols:
                cur.execute(
                    "INSERT INTO ap_match_events("
                    "invoice_id, source_json, candidates_json, chosen_json, "
                    "confidence, reasons, accepted, user_id) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (
                        int(invoice_id),
                        data.get("source_json", "{}"),
                        data.get("candidates_json", "[]"),
                        data.get("chosen_json", "{}"),
                        data.get("confidence"),
                        reason or "",
                        accepted,
                        user_id,
                    ),
                )
                conn.commit()
            return jsonify({
                "ok": True,
                "invoice_id": invoice_id,
                "accepted": accepted,
                "reason": reason,
                "user_id": user_id,
            })
    except sqlite3.Error as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/api/ap-match/confirm", methods=["POST"])
def ap_match_confirm():
    """Persist confirmed AP match links and record audit trail."""
    data = request.get_json(silent=True) or {}
    invoice_id = data.get("invoice_id") or data.get("ap_invoice_id")
    links = data.get("links") or []
    confidence = data.get("confidence")
    reasons = data.get("reasons") or []
    metadata = data.get("metadata") or {}
    user_id = (
        metadata.get("user_id")
        or data.get("user_id")
        or "system"
    ).strip()

    if not links:
        return jsonify({"error": "links_required"}), 422
    if not invoice_id:
        return jsonify({"error": "invoice_id_required"}), 422

    try:
        with db_conn() as conn:
            _ensure_tables(conn)  # creates modern schema
            # Force migration if legacy still detected (idempotent)
            _migrate_legacy_ap_po_links(conn)
            _ensure_events_table(conn)
            cur = conn.cursor()
            # Detect legacy shape runtime
            cur_cols = [
                r[1]
                for r in cur.execute(
                    "PRAGMA table_info(ap_po_links)"
                ).fetchall()
            ]
            legacy_mode = (
                'ap_invoice_id' in cur_cols and 'invoice_id' not in cur_cols
            )

            # Validación simplificada: no exceder totales de cabecera de PO
            po_totals: dict[str, float] = {}
            if _table_exists(conn, "purchase_orders_unified"):
                cur2 = conn.execute(
                    "SELECT id, COALESCE(total_amount,0) AS total_amount "
                    "FROM purchase_orders_unified"
                )
                for r in cur2.fetchall():
                    po_totals[str(r[0])] = float(r[1] or 0)
            used_per_po: dict[str, float] = {}
            for link in links:
                po_id = str(link.get("po_id"))
                amt = float(link.get("amount") or 0)
                used_per_po[po_id] = used_per_po.get(po_id, 0.0) + amt
            over_alloc = [
                {"po_id": p, "used": u, "po_total": po_totals.get(p)}
                for p, u in used_per_po.items()
                if po_totals.get(p) is not None and u > po_totals[p] + 1e-6
            ]
            if over_alloc:
                return jsonify({
                    "error": "over_allocation",
                    "violations": over_alloc,
                }), 422

            # Insert links
            for link in links:
                if legacy_mode:
                    # Map to legacy columns: ap_invoice_id, line_id, user_id
                    cur.execute(
                        "INSERT INTO ap_po_links("  # legacy shape
                        "ap_invoice_id, po_id, line_id, amount, user_id) "
                        "VALUES(?,?,?,?,?)",
                        (
                            int(invoice_id),
                            link.get("po_id"),
                            link.get("po_line_id"),
                            float(link.get("amount") or 0),
                            user_id,
                        ),
                    )
                else:
                    cur.execute(
                        "INSERT INTO ap_po_links("
                        "invoice_id, invoice_line_id, po_id, po_line_id, "
                        "amount, qty, created_by) VALUES(?,?,?,?,?,?,?)",
                        (
                            int(invoice_id),
                            link.get("invoice_line_id"),
                            link.get("po_id"),
                            link.get("po_line_id"),
                            float(link.get("amount") or 0),
                            link.get("qty"),
                            user_id,
                        ),
                    )

            event_payload = {
                "invoice_id": invoice_id,
                "links": links,
                "confidence": confidence,
                "reasons": reasons,
                "user_id": user_id,
            }
            # Events table handling (ignore if only legacy payload shape)
            ev_cols = [
                r[1]
                for r in cur.execute(
                    "PRAGMA table_info(ap_match_events)"
                ).fetchall()
            ]
            if 'invoice_id' in ev_cols:
                cur.execute(
                    "INSERT INTO ap_match_events("
                    "invoice_id, source_json, candidates_json, chosen_json, "
                    "confidence, reasons, accepted, user_id) "
                    "VALUES(?,?,?,?,?,?,1,?)",
                    (
                        int(invoice_id),
                        data.get("source_json", "{}"),
                        data.get("candidates_json", "[]"),
                        json.dumps({"links": links}, ensure_ascii=False),
                        confidence,
                        ",".join(reasons),
                        user_id,
                    ),
                )
            conn.commit()
            return jsonify({
                "ok": True,
                "invoice_id": invoice_id,
                "links_created": len(links),
                "event": event_payload,
            })
    except sqlite3.Error as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/api/ap-match/invoice/<int:invoice_id>", methods=["GET"])
def ap_match_get_invoice(invoice_id: int):
    """Devuelve links existentes y resumen para una factura AP.

    Respuesta:
        invoice_id
        links: lista de links (po_id, po_line_id, amount, qty)
        totals: por po_id (amount_sum, lines)
    """
    try:
        with db_conn() as conn:
            if not _table_exists(conn, "ap_po_links"):
                return jsonify({
                    "invoice_id": invoice_id,
                    "links": [],
                    "totals": {},
                })
            cur = conn.execute(
                "SELECT po_id, po_line_id, amount, qty "
                "FROM ap_po_links WHERE invoice_id=?",
                (invoice_id,),
            )
            rows = [dict(r) for r in cur.fetchall()]
            totals: dict[str, dict[str, Any]] = {}
            for r in rows:
                pid = str(r.get("po_id"))
                t = totals.setdefault(pid, {"amount_sum": 0.0, "lines": 0})
                t["amount_sum"] += float(r.get("amount") or 0)
                t["lines"] += 1
            for pid, t in totals.items():
                t["amount_sum"] = round(t["amount_sum"], 2)
            return jsonify({
                "invoice_id": invoice_id,
                "links": rows,
                "totals": totals,
            })
    except sqlite3.Error as e:  # noqa: BLE001
        return jsonify({"error": str(e)}), 500


@bp.route("/api/ap-match/config", methods=["GET"])
def ap_match_get_config():
    """Devuelve tolerancias efectivas para vendor/project y pesos si existen.

    Query params:
        vendor_rut, project_id
    """
    vendor_rut = request.args.get("vendor_rut")
    project_id = request.args.get("project_id")
    try:
        with db_conn() as conn:
            tol = _load_tolerances(conn, vendor_rut, project_id)
            # Extraer pesos con misma precedencia (reutilizamos lógica simple)
            weights = {"vendor": None, "amount": None, "three_way": None}
            if _table_exists(conn, "ap_match_config"):
                # Vendor override
                if vendor_rut:
                    cur = conn.execute(
                        "SELECT weight_vendor, weight_amount, weight_3way "
                        "FROM ap_match_config WHERE scope_type='vendor' "
                        "AND scope_value=? ORDER BY id DESC LIMIT 1",
                        (vendor_rut,),
                    )
                    row = cur.fetchone()
                    if row:
                        (
                            weights["vendor"],
                            weights["amount"],
                            weights["three_way"],
                        ) = row
                if project_id and weights["vendor"] is None:
                    cur = conn.execute(
                        "SELECT weight_vendor, weight_amount, weight_3way "
                        "FROM ap_match_config WHERE scope_type='project' "
                        "AND scope_value=? ORDER BY id DESC LIMIT 1",
                        (project_id,),
                    )
                    row = cur.fetchone()
                    if row and weights["vendor"] is None:
                        (
                            weights["vendor"],
                            weights["amount"],
                            weights["three_way"],
                        ) = row
                if weights["vendor"] is None:
                    cur = conn.execute(
                        "SELECT weight_vendor, weight_amount, weight_3way "
                        "FROM ap_match_config WHERE scope_type='global' "
                        "ORDER BY id DESC LIMIT 1"
                    )
                    row = cur.fetchone()
                    if row:
                        (
                            weights["vendor"],
                            weights["amount"],
                            weights["three_way"],
                        ) = row
            return jsonify({
                "effective": tol,
                "weights": weights,
                "params": {"vendor_rut": vendor_rut, "project_id": project_id},
            })
    except sqlite3.Error as e:  # noqa: BLE001
        return jsonify({"error": str(e)}), 500
