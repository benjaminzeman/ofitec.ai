"""
Blueprint EP (Estados de Pago Cliente) según playbook.

Tablas: client_contracts, client_sov_items, ep_headers, ep_lines,
ep_deductions, ep_files, ar_invoices, ar_collections.
Vistas: v_ep_approved_project, v_ar_expected_project, v_ar_actual_project.

Endpoints:
- GET  /api/projects/<int:pid>/ep
- POST /api/ep        (create EP header only)
- GET  /api/ep/<int:ep_id>         (retrieve header+lines+deductions)
- PUT  /api/ep/<int:ep_id>         (update header fields)
- POST /api/ep/<int:ep_id>/lines/bulk       (replace lines)
- POST /api/ep/<int:ep_id>/deductions/bulk  (replace deductions)
- GET  /api/ep/<int:ep_id>/summary (computed totals)
- POST /api/ep/import
- POST /api/ep/<int:ep_id>/approve
- POST /api/ep/<int:ep_id>/generate-invoice
- POST /api/ep/<int:ep_id>/generate-invoice
- POST /api/ep/<int:ep_id>/generate-sales-note (nueva relación nota de venta)
- POST /api/sales-notes/<int:sid>/issue-invoice
- POST /api/sales-notes/<int:sid>/cancel

Extras implementados (playbook):
- POST /api/ep/<int:ep_id>/files
    (vincular archivo/link)
- POST /api/contracts
    (crear contrato cliente)
- POST /api/contracts/<int:cid>/sov/import
    (cargar ítems SOV)
- POST /api/ar/invoices/<int:inv_id>/collect
    (registrar cobranza, valida over_collected)

Respuestas 422 para validaciones críticas.
"""
from __future__ import annotations

import sqlite3
import json
import hashlib
from typing import Any, Optional
from datetime import datetime, UTC
from backend.db_utils import db_conn  # shared connection manager
from dataclasses import dataclass
from flask import Blueprint, jsonify, request

try:
    # Reutilizar resolución de ruta de BD del repo si existe
    from tools.common_db import (
        existing_db_path,
        default_db_path,
    )  # type: ignore
except ImportError:  # pragma: no cover - fallback
    existing_db_path = None  # type: ignore
    default_db_path = None  # type: ignore


ep_bp = Blueprint("ep", __name__)


def _db_path() -> str:
    if existing_db_path:
        try:
            p = existing_db_path()
            if p:
                return p
        except (OSError, RuntimeError, ValueError, TypeError):
            pass
    if default_db_path:
        try:
            return default_db_path()
        except (OSError, RuntimeError, ValueError, TypeError):
            pass
    return "data/chipax_data.db"


def db() -> sqlite3.Connection:  # legacy helper (avoid wide edits)
    con = sqlite3.connect(_db_path())  # pragma: no cover
    con.row_factory = sqlite3.Row
    return con


def _ensure_schema(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    cur.executescript(
        """
        -- Contrato + SOV
        CREATE TABLE IF NOT EXISTS client_contracts (
          id INTEGER PRIMARY KEY,
          project_id INTEGER NOT NULL,
          customer_id INTEGER NOT NULL,
          code TEXT,
          start_date TEXT,
          end_date TEXT,
          currency TEXT,
          payment_terms_days INTEGER DEFAULT 30,
          retention_pct REAL DEFAULT 0,
          status TEXT CHECK (status IN ('active','closed')) DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS client_sov_items (
          id INTEGER PRIMARY KEY,
          contract_id INTEGER NOT NULL,
          item_code TEXT,
          description TEXT,
          unit TEXT,
          qty REAL,
          unit_price REAL,
          line_total REAL,
          chapter TEXT,
          UNIQUE(contract_id, item_code)
        );
        CREATE INDEX IF NOT EXISTS idx_sov_contract
            ON client_sov_items(contract_id);

        -- EP
        CREATE TABLE IF NOT EXISTS ep_headers (
          id INTEGER PRIMARY KEY,
          project_id INTEGER NOT NULL,
          contract_id INTEGER,
          ep_number TEXT,
          period_start TEXT,
          period_end TEXT,
          submitted_at TEXT,
          approved_at TEXT,
                    status TEXT CHECK (
                        status IN (
                            'draft','submitted','approved','rejected','invoiced','paid'
                        )
                    ) DEFAULT 'draft',
          retention_pct REAL,
          notes TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_ep_project ON ep_headers(project_id);
        CREATE INDEX IF NOT EXISTS idx_ep_status ON ep_headers(status);

        CREATE TABLE IF NOT EXISTS ep_lines (
          id INTEGER PRIMARY KEY,
          ep_id INTEGER NOT NULL,
          sov_item_id INTEGER,
          item_code TEXT,
          description TEXT,
          unit TEXT,
          qty_period REAL,
          unit_price REAL,
          amount_period REAL,
          qty_cum REAL,
          amount_cum REAL,
          chapter TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_ep_lines_ep ON ep_lines(ep_id);

        CREATE TABLE IF NOT EXISTS ep_deductions (
          id INTEGER PRIMARY KEY,
          ep_id INTEGER NOT NULL,
                                type TEXT CHECK (
                                    type IN (
                                        'retention','advance_amortization','penalty','other'
                                    )
                                ),
          description TEXT,
          amount REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_ep_ded_ep ON ep_deductions(ep_id);

        CREATE TABLE IF NOT EXISTS ep_files (
          id INTEGER PRIMARY KEY,
          ep_id INTEGER NOT NULL,
          drive_file_id TEXT,
          storage_url TEXT,
          kind TEXT CHECK (kind IN ('xlsx','pdf')),
          uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

                -- Notas de venta (sales notes) antes de factura AR
                CREATE TABLE IF NOT EXISTS sales_notes (
                    id INTEGER PRIMARY KEY,
                    ep_id INTEGER,
                    project_id INTEGER NOT NULL,
                    customer_id INTEGER NOT NULL,
                    note_number TEXT,
                    status TEXT CHECK (
                        status IN ('draft','issued','cancelled','invoiced')
                    ) DEFAULT 'issued',
                    amount_net REAL,
                    tax_amount REAL,
                    amount_total REAL,
                    retention_snapshot REAL,
                    metadata_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_sales_notes_ep
                    ON sales_notes(ep_id);
                CREATE INDEX IF NOT EXISTS idx_sales_notes_proj
                    ON sales_notes(project_id, status);

        -- AR
        CREATE TABLE IF NOT EXISTS ar_invoices (
          id INTEGER PRIMARY KEY,
          project_id INTEGER NOT NULL,
          customer_id INTEGER NOT NULL,
          ep_id INTEGER,
          invoice_number TEXT,
          invoice_date TEXT,
          due_date TEXT,
          amount_net REAL,
          tax_amount REAL,
          amount_total REAL,
                    status TEXT CHECK (
                        status IN ('draft','issued','paid','cancelled')
                    ) DEFAULT 'issued'
        );
        CREATE INDEX IF NOT EXISTS idx_ar_proj ON ar_invoices(project_id);
        CREATE INDEX IF NOT EXISTS idx_ar_ep ON ar_invoices(ep_id);

        CREATE TABLE IF NOT EXISTS ar_collections (
          id INTEGER PRIMARY KEY,
          invoice_id INTEGER NOT NULL,
          collected_date TEXT,
          amount REAL,
          method TEXT,
          bank_ref TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_col_inv ON ar_collections(invoice_id);

            -- Staging para importaciones EP (hoja cruda + mapping)
                CREATE TABLE IF NOT EXISTS ep_import_staging (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    contract_id INTEGER,
                                  payload_json TEXT,         -- JSON crudo
                                  column_map_json TEXT,      -- mapping
                                  inferred_fields_json TEXT, -- heurísticas
                                status TEXT CHECK(status IN (
                                    'draft','validated','promoted','error'
                                )) DEFAULT 'draft',
                    errors_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    validated_at TEXT,
                    promoted_ep_id INTEGER
                );
                        CREATE INDEX IF NOT EXISTS idx_ep_staging_proj
                            ON ep_import_staging(project_id);

                                            -- Ledger de retenciones
                                            -- (hold / release)
                                    CREATE TABLE IF NOT EXISTS
                                        ep_retention_ledger (
                                        id INTEGER PRIMARY KEY,
                                        ep_id INTEGER NOT NULL,
                                        amount REAL NOT NULL,
                                        created_at TEXT DEFAULT
                                            CURRENT_TIMESTAMP,
                                        released_at TEXT,
                                        notes TEXT
                                    );
                                    CREATE INDEX IF NOT EXISTS idx_ret_ep
                                        ON ep_retention_ledger(ep_id);
        """
    )
    # --- Extend sales_notes schema (idempotent) & create audit table
    try:
        cur.execute("PRAGMA table_info(sales_notes)")
        existing_cols = {r[1] for r in cur.fetchall()}
        # Columns to add (spec incremental). Each guarded by existence check.
        alter_statements: list[str] = []
        if "emitted_at" not in existing_cols:
            alter_statements.append("ALTER TABLE sales_notes ADD COLUMN emitted_at TEXT")
        if "approved_at" not in existing_cols:
            alter_statements.append("ALTER TABLE sales_notes ADD COLUMN approved_at TEXT")
        if "approved_by" not in existing_cols:
            alter_statements.append("ALTER TABLE sales_notes ADD COLUMN approved_by TEXT")
        if "approved_ip" not in existing_cols:
            alter_statements.append("ALTER TABLE sales_notes ADD COLUMN approved_ip TEXT")
        if "approved_ua" not in existing_cols:
            alter_statements.append("ALTER TABLE sales_notes ADD COLUMN approved_ua TEXT")
        if "pdf_hash" not in existing_cols:
            alter_statements.append("ALTER TABLE sales_notes ADD COLUMN pdf_hash TEXT")
        for stmt in alter_statements:
            try:
                cur.execute(stmt)
            except sqlite3.Error:  # pragma: no cover - best effort
                pass
        # Unique index for correlativo (will be populated later)
        try:
            cur.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_sales_notes_number ON sales_notes(note_number)"
            )
        except sqlite3.Error:
            pass
        # Audit table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sales_note_audit (
              id INTEGER PRIMARY KEY,
              sales_note_id INTEGER NOT NULL,
              action TEXT NOT NULL,
              actor TEXT,
              ip TEXT,
              user_agent TEXT,
              payload_json TEXT,
              hash_prev TEXT,
              hash_curr TEXT,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (sales_note_id) REFERENCES sales_notes(id) ON DELETE CASCADE
            );
            """
        )
        # Seed snapshot rows for existing notes without audit (lightweight)
        # We only insert if no audit rows exist at all to avoid O(N) per request.
        cur.execute("SELECT COUNT(1) FROM sales_note_audit")
        has_audit = cur.fetchone()[0] > 0
        if not has_audit:
            cur.execute("SELECT id, note_number, status, amount_total FROM sales_notes LIMIT 2500")
            rows = cur.fetchall()
            prev_hash: str | None = None
            for rid, note_number, status, amount_total in rows:
                payload = {
                    "note_number": note_number,
                    "status": status,
                    "amount_total": amount_total,
                    "seed": True,
                }
                base = f"{prev_hash or ''}|{rid}|seed|{json.dumps(payload, ensure_ascii=False, sort_keys=True)}"
                curr_hash = hashlib.sha256(base.encode('utf-8')).hexdigest()
                cur.execute(
                    "INSERT INTO sales_note_audit(sales_note_id, action, actor, payload_json, hash_prev, hash_curr) VALUES(?,?,?,?,?,?)",
                    (rid, "seed", "system", json.dumps(payload, ensure_ascii=False), prev_hash, curr_hash),
                )
                prev_hash = curr_hash
    except sqlite3.Error:  # pragma: no cover
        pass
    cur.executescript(
        """
        -- Vistas
        DROP VIEW IF EXISTS v_ep_approved_project;
        CREATE VIEW v_ep_approved_project AS
        SELECT h.project_id,
               strftime('%Y-%m-01', h.approved_at) AS bucket_month,
               SUM(l.amount_period) - COALESCE((
                 SELECT SUM(d.amount) FROM ep_deductions d WHERE d.ep_id = h.id
               ),0) AS ep_amount_net
        FROM ep_headers h
        JOIN ep_lines l ON l.ep_id = h.id
        WHERE h.status IN ('approved','invoiced','paid')
        GROUP BY h.project_id, bucket_month;

        DROP VIEW IF EXISTS v_ar_expected_project;
        CREATE VIEW v_ar_expected_project AS
        SELECT a.project_id,
               strftime('%Y-%m-01', a.due_date) AS bucket_month,
               SUM(a.amount_total) - COALESCE((
                   SELECT SUM(c.amount)
                   FROM ar_collections c
                   WHERE c.invoice_id = a.id
               ),0) AS expected_inflow
        FROM ar_invoices a
        WHERE a.status IN ('issued')
        GROUP BY a.project_id, bucket_month;

        DROP VIEW IF EXISTS v_ar_actual_project;
        CREATE VIEW v_ar_actual_project AS
        SELECT a.project_id,
               strftime('%Y-%m-01', c.collected_date) AS bucket_month,
               SUM(c.amount) AS actual_inflow
        FROM ar_collections c
        JOIN ar_invoices a ON a.id = c.invoice_id
        GROUP BY a.project_id, bucket_month;
        """
    )
    con.commit()


def _ep_exists(con: sqlite3.Connection, ep_id: int) -> bool:
    cur = con.execute("SELECT 1 FROM ep_headers WHERE id=?", (ep_id,))
    return cur.fetchone() is not None


def _lines_subtotal(con: sqlite3.Connection, ep_id: int) -> float:
    row = con.execute(
        "SELECT COALESCE(SUM(amount_period),0) FROM ep_lines WHERE ep_id=?",
        (ep_id,),
    ).fetchone()
    return float(row[0] or 0)


def _deductions_total(con: sqlite3.Connection, ep_id: int) -> float:
    row = con.execute(
        "SELECT COALESCE(SUM(amount),0) FROM ep_deductions WHERE ep_id=?",
        (ep_id,),
    ).fetchone()
    return float(row[0] or 0)


def _ep_summary(con: sqlite3.Connection, ep_id: int) -> dict:
    """Compute EP totals: lines subtotal, deductions by type, net.

    If there's no explicit 'retention' deduction but header.retention_pct
    is provided, include a computed 'retention_computed' field.
    """
    h = con.execute("SELECT * FROM ep_headers WHERE id=?", (ep_id,)).fetchone()
    if not h:
        raise Unprocessable(
            "not_found",
            "EP inexistente",
            extra={"ep_id": ep_id},
        )
    subtotal = _lines_subtotal(con, ep_id)
    # Group deductions by type
    cur = con.execute(
        (
            "SELECT type, COALESCE(SUM(amount),0) FROM ep_deductions "
            "WHERE ep_id=? GROUP BY type"
        ),
        (ep_id,),
    )
    ded_by_type: dict[str, float] = {
        str(t or "other"): float(v or 0) for t, v in cur.fetchall()
    }
    total_ded = sum(ded_by_type.values())

    # If retention is not explicitly present, compute suggestion from header
    retention_pct = float(h["retention_pct"] or 0)
    retention_computed = 0.0
    if "retention" not in ded_by_type and retention_pct > 0:
        retention_computed = round(subtotal * retention_pct, 2)

    net = max(round(subtotal - total_ded, 2), 0.0)

    # Retención ledger (held vs released)
    ret_rows = con.execute(
        "SELECT amount, released_at FROM ep_retention_ledger WHERE ep_id=?",
        (ep_id,),
    ).fetchall()
    retention_held = sum(float(r[0] or 0) for r in ret_rows if not r[1])
    retention_released = sum(float(r[0] or 0) for r in ret_rows if r[1])
    return {
        "ep": dict(h),
        "lines_subtotal": round(subtotal, 2),
        "deductions": {k: round(v, 2) for k, v in ded_by_type.items()},
        "deductions_total": round(total_ded, 2),
        "retention_computed": (
            retention_computed if retention_computed else None
        ),
        "amount_net": net,
        "retention_held": round(retention_held, 2),
        "retention_released": round(retention_released, 2),
        "retention_outstanding": round(retention_held, 2),
    }


@dataclass
class Unprocessable(ValueError):
    error: str
    detail: str | None = None
    extra: dict | None = None

    def to_payload(self) -> dict:
        data = {"error": self.error}
        if self.detail:
            data["detail"] = self.detail
        if self.extra:
            data.update(self.extra)
        return data


@ep_bp.errorhandler(Unprocessable)
def _unprocessable(e: Unprocessable):
    return jsonify(e.to_payload()), 422


@ep_bp.get("/api/projects/<int:pid>/ep")
def list_ep(pid: int):
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        rows = con.execute(
            """
            SELECT h.*,
                   (
                     SELECT COALESCE(SUM(l.amount_period),0)
                     FROM ep_lines l
                     WHERE l.ep_id = h.id
                   ) AS amount_period,
                   (
                     SELECT COALESCE(SUM(d.amount),0)
                     FROM ep_deductions d
                     WHERE d.ep_id = h.id
                   ) AS deductions
            FROM ep_headers h
            WHERE h.project_id = ?
            ORDER BY COALESCE(h.approved_at, h.submitted_at) DESC
            """,
            (pid,)
        ).fetchall()
    return jsonify({"items": [dict(r) for r in rows]})


@ep_bp.post("/api/ep")
def create_ep_header():
    """Create a minimal EP header to allow manual entry of lines/deductions.

    Body JSON: { project_id, contract_id?, ep_number?, period_start?,
                 period_end?, submitted_at?, status?, retention_pct?, notes? }
    Defaults: status=draft, submitted_at=now() when not provided.
    """
    data = request.get_json(force=True) or {}
    if not data.get("project_id"):
        raise Unprocessable("invalid_payload", "project_id requerido")
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        cur = con.cursor()
        subm = data.get("submitted_at")
        if not subm:
            subm = None  # use date('now') in SQL
        status = (data.get("status") or "draft").lower()
    # Si no se entrega retention_pct y hay contract_id, heredar valor del
    # contrato
        ret_pct = data.get("retention_pct")
        if ret_pct in (None, "", []) and data.get("contract_id"):
            try:
                rowc = cur.execute(
                    "SELECT retention_pct FROM client_contracts WHERE id=?",
                    (data.get("contract_id"),),
                ).fetchone()
                if rowc and rowc[0] is not None:
                    ret_pct = rowc[0]
            except sqlite3.Error:  # pragma: no cover - defensivo
                pass
        cur.execute(
            (
                "INSERT INTO ep_headers("
                "project_id, contract_id, ep_number, period_start, "
                "period_end, submitted_at, status, retention_pct, notes"
                ") VALUES(?,?,?,?,?, COALESCE(?, date('now')), ?, ?, ?)"
            ),
            (
                int(data["project_id"]),
                data.get("contract_id"),
                data.get("ep_number"),
                data.get("period_start"),
                data.get("period_end"),
                subm,
                status,
                ret_pct,
                data.get("notes"),
            ),
        )
        ep_id = cur.lastrowid
        con.commit()
        return jsonify({"ok": True, "ep_id": ep_id}), 201


@ep_bp.get("/api/ep/<int:ep_id>")
def get_ep(ep_id: int):
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        if not _ep_exists(con, ep_id):
            raise Unprocessable(
                "not_found",
                "EP inexistente",
                extra={"ep_id": ep_id},
            )
        h = con.execute(
            "SELECT * FROM ep_headers WHERE id=?",
            (ep_id,),
        ).fetchone()
        cur = con.execute(
            "SELECT * FROM ep_lines WHERE ep_id=? ORDER BY id",
            (ep_id,),
        )
        lines = [dict(r) for r in cur.fetchall()]
        cur = con.execute(
            "SELECT * FROM ep_deductions WHERE ep_id=? ORDER BY id",
            (ep_id,),
        )
        deductions = [dict(r) for r in cur.fetchall()]
        return jsonify({
            "header": dict(h),
            "lines": lines,
            "deductions": deductions,
        })


@ep_bp.put("/api/ep/<int:ep_id>")
def update_ep_header(ep_id: int):
    """Update editable header fields: ep_number, period_start, period_end,
    submitted_at, approved_at (only when status is approved), status,
    retention_pct, notes, contract_id.
    """
    data = request.get_json(force=True) or {}
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        if not _ep_exists(con, ep_id):
            raise Unprocessable(
                "not_found",
                "EP inexistente",
                extra={"ep_id": ep_id},
            )
        # Build dynamic UPDATE
        allowed = {
            "ep_number",
            "period_start",
            "period_end",
            "submitted_at",
            "approved_at",
            "status",
            "retention_pct",
            "notes",
            "contract_id",
        }
        sets = []
        params = []
        for k, v in data.items():
            if k in allowed:
                sets.append(f"{k} = ?")
                params.append(v)
        if not sets:
            return jsonify({"ok": True, "updated": 0})
        params.append(ep_id)
        sql = "UPDATE ep_headers SET " + ", ".join(sets) + " WHERE id=?"
        con.execute(sql, params)
        con.commit()
        return jsonify({"ok": True, "updated": len(sets)})


@ep_bp.post("/api/ep/<int:ep_id>/lines/bulk")
def set_ep_lines(ep_id: int):
    """Replace lines for an EP in bulk. Validates against contract SOV caps.

    Body:
    {
      lines: [
        { item_code?, description?, unit?, qty_period?, unit_price?,
          amount_period?, qty_cum?, amount_cum?, chapter? }, ...
      ],
      validate_contract: true|false
    }
    """
    payload = request.get_json(force=True) or {}
    lines = payload.get("lines") or []
    if not isinstance(lines, list):
        raise Unprocessable("invalid_payload", "lines debe ser lista")
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        if not _ep_exists(con, ep_id):
            raise Unprocessable(
                "not_found",
                "EP inexistente",
                extra={"ep_id": ep_id},
            )
        cur = con.cursor()
        # Obtain contract_id from EP
        row = cur.execute(
            "SELECT contract_id FROM ep_headers WHERE id=?",
            (ep_id,),
        ).fetchone()
        contract_id = row[0] if row else None
        sov_caps: dict[str, float] = {}
        prev_approved: dict[str, float] = {}
        if contract_id:
            sov_caps = {
                r[0]: float(r[1] or 0)
                for r in cur.execute(
                    (
                        "SELECT item_code, COALESCE(line_total,0) "
                        "FROM client_sov_items WHERE contract_id=?"
                    ),
                    (contract_id,),
                ).fetchall()
            }
            prev_approved = {
                r[0]: float(r[1] or 0)
                for r in cur.execute(
                    (
                        "SELECT l.item_code, COALESCE(SUM(l.amount_period),0) "
                        "FROM ep_lines l JOIN ep_headers h ON h.id=l.ep_id "
                        "WHERE h.contract_id=? AND h.status IN("
                        "'approved','invoiced','paid') GROUP BY l.item_code"
                    ),
                    (contract_id,),
                ).fetchall()
            }
        # Replace lines
        cur.execute("DELETE FROM ep_lines WHERE ep_id=?", (ep_id,))
        for ln in lines:
            amt = ln.get("amount_period")
            if (
                amt is None
                and ln.get("qty_period") is not None
                and ln.get("unit_price") is not None
            ):
                try:
                    amt = float(ln["qty_period"]) * float(ln["unit_price"])
                except (TypeError, ValueError):
                    amt = None
            code = ln.get("item_code")
            if contract_id and code and code in sov_caps:
                cap = float(sov_caps.get(code) or 0)
                prev_amt = float(prev_approved.get(code, 0))
                if (prev_amt + float(amt or 0)) > (cap + 1e-6):
                    raise Unprocessable(
                        "ep_exceeds_contract_item",
                        f"Item {code} excede SOV",
                        extra={
                            "item_code": code,
                            "cap": cap,
                            "prev": prev_amt,
                            "attempt": float(amt or 0),
                        },
                    )
            cur.execute(
                (
                    "INSERT INTO ep_lines("
                    "ep_id, sov_item_id, item_code, description, unit, "
                    "qty_period, unit_price, amount_period, qty_cum, "
                    "amount_cum, chapter) VALUES(?,?,?,?,?,?,?,?,?,?,?)"
                ),
                (
                    ep_id,
                    ln.get("sov_item_id"),
                    code,
                    ln.get("description"),
                    ln.get("unit"),
                    ln.get("qty_period"),
                    ln.get("unit_price"),
                    amt,
                    ln.get("qty_cum"),
                    ln.get("amount_cum"),
                    ln.get("chapter"),
                ),
            )
        con.commit()
        return jsonify({"ok": True, "count": len(lines)})


@ep_bp.post("/api/ep/<int:ep_id>/deductions/bulk")
def set_ep_deductions(ep_id: int):
    """Replace deductions for an EP in bulk.

    Body: { deductions: [ { type, description?, amount }, ... ] }
    """
    payload = request.get_json(force=True) or {}
    deductions = payload.get("deductions") or []
    if not isinstance(deductions, list):
        raise Unprocessable("invalid_payload", "deductions debe ser lista")
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        if not _ep_exists(con, ep_id):
            raise Unprocessable(
                "not_found",
                "EP inexistente",
                extra={"ep_id": ep_id},
            )
        cur = con.cursor()
        cur.execute("DELETE FROM ep_deductions WHERE ep_id=?", (ep_id,))
        for d in deductions:
            cur.execute(
                (
                    "INSERT INTO ep_deductions("
                    "ep_id, type, description, amount"
                    ") VALUES(?,?,?,?)"
                ),
                (
                    ep_id,
                    d.get("type"),
                    d.get("description"),
                    d.get("amount"),
                ),
            )
        con.commit()
        return jsonify({"ok": True, "count": len(deductions)})


@ep_bp.get("/api/ep/<int:ep_id>/summary")
def ep_summary(ep_id: int):
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        if not _ep_exists(con, ep_id):
            raise Unprocessable(
                "not_found",
                "EP inexistente",
                extra={"ep_id": ep_id},
            )
        return jsonify(_ep_summary(con, ep_id))


@ep_bp.post("/api/ep/<int:ep_id>/files")
def ep_attach_file(ep_id: int):
    """Vincula un archivo (Drive URL o storage_url) al EP.

    Body JSON: { drive_file_id?, storage_url?, kind: 'xlsx'|'pdf' }
    """
    data = request.get_json(force=True) or {}
    kind = (data.get("kind") or "").lower()
    if kind not in ("xlsx", "pdf"):
        raise Unprocessable("invalid_payload", "kind debe ser xlsx|pdf")
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        cur = con.cursor()
        row = cur.execute(
            "SELECT id FROM ep_headers WHERE id=?",
            (ep_id,),
        ).fetchone()
        if not row:
            raise Unprocessable(
                "not_found",
                "EP inexistente",
                extra={"ep_id": ep_id},
            )
        cur.execute(
            (
                "INSERT INTO ep_files("
                "ep_id, drive_file_id, storage_url, kind, uploaded_at) "
                "VALUES(?,?,?,?, datetime('now'))"
            ),
            (ep_id, data.get("drive_file_id"), data.get("storage_url"), kind),
        )
        con.commit()
        return jsonify({"ok": True})


@ep_bp.post("/api/contracts")
def create_contract():
    """Crea un contrato cliente mínimo.

    Body JSON: { project_id, customer_id, code?, start_date?, end_date?,
    currency?, payment_terms_days?, retention_pct? }
    """
    data = request.get_json(force=True) or {}
    req = (data.get("project_id"), data.get("customer_id"))
    if not all(req):
        raise Unprocessable(
            "invalid_payload",
            "project_id y customer_id son requeridos",
        )
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        cur = con.cursor()
        cur.execute(
            (
                "INSERT INTO client_contracts("
                "project_id, customer_id, code, start_date, end_date,"
                " currency, payment_terms_days, retention_pct, status) "
                "VALUES(?,?,?,?,?,?,?,?, 'active')"
            ),
            (
                int(data["project_id"]),
                int(data["customer_id"]),
                data.get("code"),
                data.get("start_date"),
                data.get("end_date"),
                data.get("currency"),
                int(data.get("payment_terms_days", 30)),
                float(data.get("retention_pct", 0) or 0),
            ),
        )
        cid = cur.lastrowid
        con.commit()
        return jsonify({"ok": True, "contract_id": cid})


@ep_bp.post("/api/contracts/<int:cid>/sov/import")
def sov_import(cid: int):
    """Carga masiva de ítems SOV para un contrato.

    Body JSON: { items: [{ item_code, description?, unit?, qty?, unit_price?,
    line_total?, chapter? }, ...] }
    Calcula line_total si viene qty y unit_price.
    """
    data = request.get_json(force=True) or {}
    items = data.get("items") or []
    if not isinstance(items, list) or not items:
        raise Unprocessable("invalid_payload", "items requerido")
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        cur = con.cursor()
        # Validar existencia del contrato
        row = cur.execute(
            "SELECT id FROM client_contracts WHERE id=?",
            (cid,),
        ).fetchone()
        if not row:
            raise Unprocessable(
                "not_found",
                "Contrato inexistente",
                extra={"contract_id": cid},
            )
        inserted = 0
        for ln in items:
            code = ln.get("item_code")
            if not code:
                continue
            qty = ln.get("qty")
            up = ln.get("unit_price")
            total = ln.get("line_total")
            if total is None and qty is not None and up is not None:
                try:
                    total = float(qty) * float(up)
                except (TypeError, ValueError):
                    total = None
            try:
                cur.execute(
                    (
                        "INSERT OR REPLACE INTO client_sov_items("
                        "contract_id, item_code, description, unit, qty,"
                        " unit_price, line_total, chapter"
                        ") VALUES(?,?,?,?,?,?,?,?)"
                    ),
                    (
                        cid,
                        code,
                        ln.get("description"),
                        ln.get("unit"),
                        qty,
                        up,
                        total,
                        ln.get("chapter"),
                    ),
                )
                inserted += 1
            except sqlite3.Error:
                continue
        con.commit()
        return jsonify({"ok": True, "inserted": inserted})


@ep_bp.post("/api/ar/invoices/<int:invoice_id>/collect")
def ar_collect(invoice_id: int):
    """Registra una cobranza sobre una factura.

    Valida no sobrepasar el total (over_collected).
    """
    data = request.get_json(force=True) or {}
    amount = float(data.get("amount") or 0)
    if amount <= 0:
        raise Unprocessable("invalid_payload", "amount debe ser > 0")
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        cur = con.cursor()
        inv = cur.execute(
            "SELECT id, amount_total, status FROM ar_invoices WHERE id=?",
            (invoice_id,),
        ).fetchone()
        if not inv:
            raise Unprocessable(
                "not_found",
                "Factura inexistente",
                extra={"invoice_id": invoice_id},
            )
        # Suma cobrado previo
        row = cur.execute(
            "SELECT COALESCE(SUM(amount),0) FROM ar_collections "
            "WHERE invoice_id=?",
            (invoice_id,),
        ).fetchone()
        collected = float(row[0] or 0)
        total = float(inv[1] or 0)
        if collected + amount > total + 1e-6:
            raise Unprocessable(
                "over_collected",
                "Cobro supera total de factura",
                extra={
                    "invoice_id": invoice_id,
                    "total": total,
                    "collected": collected,
                    "attempt": amount,
                },
            )
        cur.execute(
            (
                "INSERT INTO ar_collections("
                "invoice_id, collected_date, amount, method, bank_ref) "
                "VALUES(?, date('now'), ?, ?, ?)"
            ),
            (invoice_id, amount, data.get("method"), data.get("bank_ref")),
        )
        # Si quedó completamente cobrada, marcar como paid
        if collected + amount >= total - 1e-6:
            cur.execute(
                "UPDATE ar_invoices SET status='paid' WHERE id=?",
                (invoice_id,),
            )
        con.commit()
        return jsonify({"ok": True})


@ep_bp.post("/api/ep/import")
def import_ep():
    data = request.get_json(force=True) or {}
    header = data.get("header")
    lines = data.get("lines", [])
    deductions = data.get("deductions", [])
    if not header or not lines:
        raise Unprocessable("invalid_payload", "header or lines missing")

    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO ep_headers(
                project_id, contract_id, ep_number, period_start, period_end,
                submitted_at, status, retention_pct, notes
            ) VALUES(?,?,?,?,?, date('now'), 'submitted', ?, ?)
            """,
            (
                header["project_id"],
                header.get("contract_id"),
                header.get("ep_number"),
                header.get("period_start"),
                header.get("period_end"),
                header.get("retention_pct"),
                header.get("notes"),
            ),
        )
        ep_id = cur.lastrowid

        # Validación contra contrato/SOV si existe
        if header.get("contract_id"):
            sov = {
                r["item_code"]: r
                for r in con.execute(
                    (
                        "SELECT i.item_code, i.line_total "
                        "FROM client_sov_items i WHERE i.contract_id=?"
                    ),
                    (header["contract_id"],),
                )
            }
            prev = {
                r["item_code"]: r["amount_cum"]
                for r in con.execute(
                    (
                        "SELECT l.item_code, "
                        "COALESCE(SUM(l.amount_period),0) AS amount_cum "
                        "FROM ep_lines l JOIN ep_headers h ON h.id=l.ep_id "
                        "WHERE h.contract_id=? "
                        "AND h.status IN('approved','invoiced','paid') "
                        "GROUP BY l.item_code"
                    ),
                    (header["contract_id"],),
                )
            }
        else:
            sov, prev = {}, {}

        for ln in lines:
            amt = ln.get("amount_period")
            if (
                amt is None
                and ln.get("qty_period") is not None
                and ln.get("unit_price") is not None
            ):
                amt = float(ln["qty_period"]) * float(ln["unit_price"])

            code = ln.get("item_code")
            if code in sov:
                cap = float(sov[code]["line_total"])
                prev_amt = float(prev.get(code, 0))
                if prev_amt + float(amt or 0) > cap + 1e-6:
                    raise Unprocessable(
                        "ep_exceeds_contract_item",
                        f"Item {code} excede SOV",
                        extra={
                            "item_code": code,
                            "cap": cap,
                            "prev": prev_amt,
                            "attempt": amt,
                        },
                    )

            cur.execute(
                """
                INSERT INTO ep_lines(
                    ep_id, sov_item_id, item_code, description, unit,
                    qty_period, unit_price, amount_period, qty_cum,
                    amount_cum, chapter
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    ep_id,
                    ln.get("sov_item_id"),
                    code,
                    ln.get("description"),
                    ln.get("unit"),
                    ln.get("qty_period"),
                    ln.get("unit_price"),
                    amt,
                    ln.get("qty_cum"),
                    ln.get("amount_cum"),
                    ln.get("chapter"),
                ),
            )

        for d in deductions:
            cur.execute(
                (
                    "INSERT INTO ep_deductions("
                    "ep_id, type, description, amount) "
                    "VALUES(?,?,?,?)"
                ),
                (ep_id, d.get("type"), d.get("description"), d.get("amount")),
            )

        con.commit()
        return jsonify({"ok": True, "ep_id": ep_id})


# ------------------------------
# EP Import Staging Flow
# ------------------------------

@ep_bp.post("/api/ep/import/staging")
def ep_import_staging_create():
    """Crea un registro de staging con los datos crudos de una planilla.

    Body JSON:
      project_id (req), contract_id?, rows: [ { ... columnas.xls ... }, ... ],
      column_map?: { logical_field: source_header },
      infer?: bool (default True) → intenta detectar qty/unit_price/amount.

    Retorna staging_id y un suggestion de mapping si no se entregó.
    """
    data = request.get_json(force=True) or {}
    project_id = data.get("project_id")
    rows = data.get("rows") or []
    if not project_id or not isinstance(rows, list) or not rows:
        raise Unprocessable("invalid_payload", "project_id y rows requeridos")
    column_map = data.get("column_map") or {}
    infer = bool(data.get("infer", True))
    # Heurística simple: buscar cabeceras por lower substrings
    
    def _infer_map(first_row: dict[str, Any]) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for k in first_row.keys():
            kl = str(k).strip().lower()
            if "codigo" in kl or kl in ("item", "code"):
                mapping.setdefault("item_code", k)
            if kl.startswith("desc") or "descripcion" in kl:
                mapping.setdefault("description", k)
            if kl in ("unidad", "unit"):
                mapping.setdefault("unit", k)
            if kl.startswith("cant") or kl.startswith("qty"):
                mapping.setdefault("qty_period", k)
            if "precio" in kl or "unit_price" in kl or kl == "precio unitario":
                mapping.setdefault("unit_price", k)
            if "monto" in kl or kl == "amount" or kl == "total":
                mapping.setdefault("amount_period", k)
            if "capitulo" in kl or kl == "chapter":
                mapping.setdefault("chapter", k)
        return mapping
    inferred_map = {}
    if infer and rows:
        try:
            inferred_map = _infer_map(rows[0])
        except (KeyError, ValueError, TypeError):
            inferred_map = {}
    # Merge precedence: explicit column_map overrides inferred
    final_map = {**inferred_map, **column_map}
    # usar json global ya importado
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO ep_import_staging(
              project_id, contract_id, payload_json, column_map_json,
              inferred_fields_json, status
            ) VALUES(?,?,?,?,?, 'draft')
            """,
            (
                int(project_id),
                data.get("contract_id"),
                json.dumps(rows, ensure_ascii=False),
                json.dumps(final_map, ensure_ascii=False),
                json.dumps({"inferred": inferred_map}, ensure_ascii=False),
            ),
        )
        sid = cur.lastrowid
        con.commit()
        return jsonify({
            "ok": True,
            "staging_id": sid,
            "column_map": final_map,
            "inferred": inferred_map,
        }), 201


@ep_bp.post("/api/ep/import/staging/<int:staging_id>/validate")
def ep_import_staging_validate(staging_id: int):
    """Valida un staging usando el mapping guardado. Calcula montos y
    simula restricciones de contrato (si contract_id presente).

    Devuelve totales y lista de potenciales violaciones por item.
    """
    # usar json global
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        cur = con.cursor()
        row = cur.execute(
            "SELECT * FROM ep_import_staging WHERE id=?",
            (staging_id,),
        ).fetchone()
        if not row:
            raise Unprocessable("not_found", "staging inexistente")
        payload = json.loads(row["payload_json"] or "[]")
        cmap = json.loads(row["column_map_json"] or "{}")
        contract_id = row["contract_id"]
        violations: list[dict] = []
        sov_caps: dict[str, float] = {}
        prev_approved: dict[str, float] = {}
        if contract_id:
            sov_caps = {
                r[0]: float(r[1] or 0)
                for r in cur.execute(
                    "SELECT item_code, COALESCE(line_total,0) "
                    "FROM client_sov_items WHERE contract_id=?",
                    (contract_id,),
                ).fetchall()
            }
            prev_approved = {
                r[0]: float(r[1] or 0)
                for r in cur.execute(
                    """
                                  SELECT l.item_code,
                                      COALESCE(SUM(l.amount_period),0)
                                  FROM ep_lines l
                                  JOIN ep_headers h ON h.id=l.ep_id
                                        WHERE h.contract_id=? AND h.status IN (
                                            'approved','invoiced','paid'
                                        )
                    GROUP BY l.item_code
                    """,
                    (contract_id,),
                ).fetchall()
            }
        total = 0.0
        normalized: list[dict] = []
        for src in payload:
            item = {}
            for logical, src_key in cmap.items():
                item[logical] = src.get(src_key)
            # try compute amount if missing
            if (
                item.get("amount_period") in (None, "")
                and item.get("qty_period") not in (None, "")
                and item.get("unit_price") not in (None, "")
            ):
                try:
                    item["amount_period"] = (
                        float(item["qty_period"]) * float(item["unit_price"])
                    )
                except (ValueError, TypeError):
                    pass
            try:
                amt = float(item.get("amount_period") or 0)
            except (ValueError, TypeError):
                amt = 0.0
            total += amt
            code = item.get("item_code")
            if code and code in sov_caps:
                cap = sov_caps[code]
                prev_amt = prev_approved.get(code, 0.0)
                if prev_amt + amt > cap + 1e-6:
                    violations.append({
                        "error": "ep_exceeds_contract_item",
                        "item_code": code,
                        "cap": cap,
                        "prev": prev_amt,
                        "attempt": amt,
                    })
            normalized.append(item)
        status = "validated"
        cur.execute(
            "UPDATE ep_import_staging SET status=?, "
            "validated_at=datetime('now'), errors_json=? WHERE id=?",
            (status, json.dumps(violations, ensure_ascii=False), staging_id),
        )
        con.commit()
        return jsonify({
            "ok": True,
            "staging_id": staging_id,
            "total_amount": round(total, 2),
            "violations": violations,
            "sample": normalized[:10],
        })


@ep_bp.post("/api/ep/import/staging/<int:staging_id>/promote")
def ep_import_staging_promote(staging_id: int):
    """Promueve un staging validado creando un EP real (similar a import_ep).
    Reutiliza mapping y respeta violaciones; si hay violaciones severas -> 422.
    """
    # usar json global
    body = request.get_json(silent=True) or {}
    header_extra = body.get("header") or {}
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        cur = con.cursor()
        row = cur.execute(
            "SELECT * FROM ep_import_staging WHERE id=?",
            (staging_id,),
        ).fetchone()
        if not row:
            raise Unprocessable("not_found", "staging inexistente")
        if row["status"] not in ("validated", "draft"):
            raise Unprocessable(
                "invalid_state",
                "staging no válido para promote",
            )
        violations = []
        if row["errors_json"]:
            try:
                violations = json.loads(row["errors_json"])
            except (ValueError, TypeError):
                violations = []
        if any(
            v.get("error") == "ep_exceeds_contract_item" for v in violations
        ):
            raise Unprocessable(
                "violations_present",
                "Resolver violaciones antes de promover",
                extra={"violations": violations},
            )
        payload = json.loads(row["payload_json"] or "[]")
        cmap = json.loads(row["column_map_json"] or "{}")
        project_id = row["project_id"]
        contract_id = row["contract_id"]
        # Crear EP header
        cur.execute(
            """
            INSERT INTO ep_headers(
              project_id, contract_id, ep_number, period_start, period_end,
              submitted_at, status, retention_pct, notes
            ) VALUES(?,?,?,?,?, date('now'), 'submitted', ?, ?)
            """,
            (
                project_id,
                contract_id,
                header_extra.get("ep_number"),
                header_extra.get("period_start"),
                header_extra.get("period_end"),
                header_extra.get("retention_pct"),
                header_extra.get("notes"),
            ),
        )
        ep_id = cur.lastrowid
        # Insert lines usando mapping
        for src in payload:
            ln = {}
            for logical, src_key in cmap.items():
                ln[logical] = src.get(src_key)
            if (
                ln.get("amount_period") in (None, "")
                and ln.get("qty_period") not in (None, "")
                and ln.get("unit_price") not in (None, "")
            ):
                try:
                    ln["amount_period"] = (
                        float(ln["qty_period"]) * float(ln["unit_price"])
                    )
                except (ValueError, TypeError):
                    pass
            cur.execute(
                """
                INSERT INTO ep_lines(
                  ep_id, sov_item_id, item_code, description, unit,
                  qty_period, unit_price, amount_period, qty_cum,
                  amount_cum, chapter
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    ep_id,
                    ln.get("sov_item_id"),
                    ln.get("item_code"),
                    ln.get("description"),
                    ln.get("unit"),
                    ln.get("qty_period"),
                    ln.get("unit_price"),
                    ln.get("amount_period"),
                    ln.get("qty_cum"),
                    ln.get("amount_cum"),
                    ln.get("chapter"),
                ),
            )
        cur.execute(
            "UPDATE ep_import_staging SET status='promoted', "
            "promoted_ep_id=? WHERE id=?",
            (ep_id, staging_id),
        )
        con.commit()
        return jsonify({"ok": True, "ep_id": ep_id, "staging_id": staging_id})


@ep_bp.post("/api/ep/<int:ep_id>/approve")
def approve_ep(ep_id: int):
    with db_conn(_db_path()) as con:
        cur = con.cursor()
        row = cur.execute(
            "SELECT status FROM ep_headers WHERE id=?",
            (ep_id,),
        ).fetchone()
        if not row:
            raise Unprocessable(
                "not_found",
                "EP inexistente",
                extra={"ep_id": ep_id},
            )
        if row["status"] not in ("draft", "submitted"):
            raise Unprocessable(
                "invalid_state",
                f"No se puede aprobar desde {row['status']}",
            )
        cur.execute(
            (
                "UPDATE ep_headers SET status='approved', "
                "approved_at=date('now') WHERE id=?"
            ),
            (ep_id,),
        )
        con.commit()
        return jsonify({"ok": True, "ep_id": ep_id, "status": "approved"})


@ep_bp.post("/api/ep/<int:ep_id>/generate-invoice")
def ep_to_invoice(ep_id: int):
    TAX_RATE = 0.19  # IVA por defecto; parametrizable en configuración
    with db_conn(_db_path()) as con:
        cur = con.cursor()
        h = cur.execute(
            "SELECT * FROM ep_headers WHERE id=?",
            (ep_id,),
        ).fetchone()
        if not h:
            raise Unprocessable(
                "not_found",
                "EP inexistente",
                extra={"ep_id": ep_id},
            )
        # Permitimos intentar generar (o detectar duplicado) si el EP ya
        # está aprobado, invoiced o incluso pagado (para devolver
        # duplicate_invoice en lugar de invalid_state en reintentos).
        if h["status"] not in ("approved", "invoiced", "paid"):
            raise Unprocessable(
                "invalid_state",
                f"EP no está en estado válido (actual: {h['status']})",
            )

        # Duplicate invoice guard: reject if an active invoice already exists
        dup = cur.execute(
            (
                "SELECT id FROM ar_invoices "
                "WHERE ep_id = ? AND status IN ("  # active invoice present
                "'issued','paid','cancelled','draft') LIMIT 1"
            ),
            (ep_id,),
        ).fetchone()
        if dup:
            raise Unprocessable(
                "duplicate_invoice",
                "EP ya tiene factura emitida",
                extra={"invoice_id": dup[0], "ep_id": ep_id},
            )

        sums = cur.execute(
            (
                "SELECT COALESCE(SUM(l.amount_period),0) AS amt "
                "FROM ep_lines l WHERE l.ep_id=?"
            ),
            (ep_id,),
        ).fetchone()
        ded = cur.execute(
            (
                "SELECT COALESCE(SUM(d.amount),0) AS ded "
                "FROM ep_deductions d WHERE d.ep_id=?"
            ),
            (ep_id,),
        ).fetchone()
        net = float(sums["amt"] or 0) - float(ded["ded"] or 0)
        if net < 0:
            net = 0.0
        if net == 0.0:
            raise Unprocessable(
                "zero_amount_invoice",
                "EP no tiene monto neto para facturar",
                extra={"ep_id": ep_id},
            )
        tax = round(net * TAX_RATE, 2)
        total = round(net + tax, 2)

        # Due date por términos de pago (si existe contrato)
        days = 30
        customer_id = 0
        if h["contract_id"]:
            ptd = cur.execute(
                (
                    "SELECT COALESCE(payment_terms_days,30) AS d, "
                    "COALESCE(customer_id,0) AS cust "
                    "FROM client_contracts WHERE id=?"
                ),
                (h["contract_id"],),
            ).fetchone()
            if ptd:
                days = int(ptd["d"] or 30)
                customer_id = int(ptd["cust"] or 0)

        cur.execute(
            (
                "INSERT INTO ar_invoices("
                "project_id, customer_id, ep_id, invoice_number, "
                "invoice_date, due_date, amount_net, tax_amount, "
                "amount_total, status) "
                "VALUES(?,?,?,?, date('now'), date('now','+'||?||' day'), "
                "?, ?, ?, 'issued')"
            ),
            (h["project_id"], customer_id, ep_id, None, days, net, tax, total),
        )
        inv_id = cur.lastrowid
        # Si existe sales_note 'issued' asociada al EP marcar 'invoiced'
        sn_row = cur.execute(
            (
                "SELECT id FROM sales_notes WHERE ep_id=? "
                "AND status='issued' LIMIT 1"
            ),
            (ep_id,),
        ).fetchone()
        if sn_row:
            cur.execute(
                (
                    "UPDATE sales_notes SET status='invoiced', "
                    "updated_at=datetime('now') WHERE id=?"
                ),
                (sn_row[0],),
            )
        cur.execute(
            "UPDATE ep_headers SET status='invoiced' WHERE id=?",
            (ep_id,),
        )
    # Registrar retención en ledger (si existe deducción retention
    # o cálculo sugerido)
        # 1. Buscar deducción explícita
        ret_row = cur.execute(
            "SELECT COALESCE(SUM(amount),0) FROM ep_deductions "
            "WHERE ep_id=? AND type='retention'",
            (ep_id,),
        ).fetchone()
        explicit_ret = float(ret_row[0] or 0)
        retention_amount = explicit_ret
        if retention_amount <= 0:
            # Calcular sugerida si header.retention_pct
            # Necesitamos subtotal líneas
            lines_sum = cur.execute(
                "SELECT COALESCE(SUM(amount_period),0) FROM ep_lines "
                "WHERE ep_id=?",
                (ep_id,),
            ).fetchone()
            lines_subtotal = float(lines_sum[0] or 0)
            rpct = float(h["retention_pct"] or 0)
            if rpct > 0:
                retention_amount = round(lines_subtotal * rpct, 2)
        if retention_amount > 0:
            # Evitar duplicar si ya existe ledger (defensivo, la guardia de
            # factura impide reingreso)
            existing_ledger = cur.execute(
                "SELECT 1 FROM ep_retention_ledger WHERE ep_id=? LIMIT 1",
                (ep_id,),
            ).fetchone()
            if not existing_ledger:
                cur.execute(
                    "INSERT INTO ep_retention_ledger(ep_id, amount, notes) "
                    "VALUES(?,?,?)",
                    (ep_id, retention_amount, "auto ledger on invoice"),
                )
        con.commit()
        return jsonify(
            {
                "ok": True,
                "invoice_id": inv_id,
                "amount_net": net,
                "tax_amount": tax,
                "amount_total": total,
                "retention_recorded": (
                    retention_amount if retention_amount > 0 else None
                ),
            }
        )


# ------------------------------
# Sales Notes (Notas de Venta)
# ------------------------------

@ep_bp.post("/api/ep/<int:ep_id>/generate-sales-note")
def ep_generate_sales_note(ep_id: int):
    """Genera una nota de venta (sales_note) preliminar para un EP.

    Reglas:
      - EP debe existir y estar en estado 'submitted' o 'approved'.
      - No debe existir otra sales_note 'issued' o 'invoiced' para el EP.
    Montos: recalculados al momento (similar a factura) con IVA 19%.
    """
    TAX_RATE = 0.19
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        cur = con.cursor()
        h = cur.execute(
            "SELECT * FROM ep_headers WHERE id=?", (ep_id,)
        ).fetchone()
        if not h:
            raise Unprocessable(
                "not_found", "EP inexistente", extra={"ep_id": ep_id}
            )
        if h["status"] not in ("submitted", "approved"):
            raise Unprocessable(
                "invalid_state",
                f"EP no está en estado válido (actual: {h['status']})",
            )
        dup = cur.execute(
            (
                "SELECT id FROM sales_notes WHERE ep_id=? "
                "AND status IN ('issued','invoiced') LIMIT 1"
            ),
            (ep_id,),
        ).fetchone()
        if dup:
            raise Unprocessable(
                "sales_note_exists",
                "EP ya tiene nota de venta",
                extra={"sales_note_id": dup[0], "ep_id": ep_id},
            )
        # Calcular montos desde líneas/deducciones
        lines_sum = cur.execute(
            (
                "SELECT COALESCE(SUM(amount_period),0) "
                "FROM ep_lines WHERE ep_id=?"
            ),
            (ep_id,),
        ).fetchone()
        subtotal = float(lines_sum[0] or 0)
        ded_sum = cur.execute(
            "SELECT COALESCE(SUM(amount),0) FROM ep_deductions WHERE ep_id=?",
            (ep_id,),
        ).fetchone()
        deductions_total = float(ded_sum[0] or 0)
        net = max(subtotal - deductions_total, 0.0)
        if net <= 0:
            raise Unprocessable(
                "zero_amount_sales_note",
                "EP no tiene monto neto para nota de venta",
                extra={"ep_id": ep_id},
            )
        tax = round(net * TAX_RATE, 2)
        total = round(net + tax, 2)
        # Retención snapshot (deducción explícita o computada)
        retention_snapshot = 0.0
        ret_row = cur.execute(
            (
                "SELECT COALESCE(SUM(amount),0) FROM ep_deductions "
                "WHERE ep_id=? AND type='retention'"
            ),
            (ep_id,),
        ).fetchone()
        explicit_ret = float(ret_row[0] or 0)
        if explicit_ret > 0:
            retention_snapshot = explicit_ret
        else:
            rpct = float(h["retention_pct"] or 0)
            if rpct > 0:
                retention_snapshot = round(subtotal * rpct, 2)
        # customer_id via contrato si existe
        customer_id = 0
        if h["contract_id"]:
            crow = cur.execute(
                "SELECT customer_id FROM client_contracts WHERE id=?",
                (h["contract_id"],),
            ).fetchone()
            if crow:
                customer_id = int(crow[0] or 0)
        cur.execute(
            (
                "INSERT INTO sales_notes("  # columns
                "ep_id, project_id, customer_id, note_number, status, "
                "amount_net, tax_amount, amount_total, retention_snapshot, "
                "metadata_json) VALUES(?,?,?,?, 'draft', ?, ?, ?, ?, ?)"
            ),
            (
                ep_id,
                h["project_id"],
                customer_id,
                None,  # correlativo se asigna al aprobar
                net,
                tax,
                total,
                retention_snapshot,
                None,
            ),
        )
        sid = cur.lastrowid
        _append_sales_note_audit(cur, int(sid), "create_draft", payload={
            "amount_net": net,
            "tax_amount": tax,
            "amount_total": total,
            "retention_snapshot": retention_snapshot,
        })
        con.commit()
        return jsonify(
            {
                "ok": True,
                "sales_note_id": sid,
                "ep_id": ep_id,
                "amount_net": net,
                "tax_amount": tax,
                "amount_total": total,
                "retention_snapshot": retention_snapshot,
                "status": "draft",
            }
        ), 201


@ep_bp.get("/api/sales-notes/<int:sid>")
def get_sales_note(sid: int):
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        cur = con.cursor()
        row = cur.execute(
            "SELECT * FROM sales_notes WHERE id=?", (sid,)
        ).fetchone()
        if not row:
            raise Unprocessable(
                "sales_note_not_found",
                "Nota de venta inexistente",
                extra={"sales_note_id": sid},
            )
        return jsonify(dict(row))


@ep_bp.get("/api/sales-notes")
def list_sales_notes():
    """Listado simple de notas de venta.

    Query params opcionales:
      - status: filtra por estado exacto (issued, invoiced, cancelled)
      - ep_id: filtra por EP específico
      - project_id: filtra por proyecto
      - limit: máximo de filas (defecto 100, máx 500)
    Retorna items ordenados por id DESC.
    """
    status = request.args.get("status")
    ep_id = request.args.get("ep_id")
    project_id = request.args.get("project_id")
    try:
        limit = int(request.args.get("limit", "100"))
    except (TypeError, ValueError):  # noqa: PERF203
        limit = 100
    limit = max(1, min(500, limit))
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        cur = con.cursor()
        where = ["1=1"]
        params: list = []
        if status:
            where.append("status = ?")
            params.append(status)
        if ep_id:
            try:
                params.append(int(ep_id))
                where.append("ep_id = ?")
            except (TypeError, ValueError):
                return jsonify({"items": [], "error": "invalid_ep_id"}), 400
        if project_id:
            where.append("project_id = ?")
            params.append(project_id)
        sql = (
            "SELECT id, ep_id, project_id, status, amount_net, tax_amount, "
            "amount_total, retention_snapshot, created_at, updated_at "
            "FROM sales_notes WHERE "
            + " AND ".join(where)
            + " ORDER BY id DESC LIMIT ?"
        )
        params.append(limit)
        rows = [dict(r) for r in cur.execute(sql, params).fetchall()]
        return jsonify({"items": rows, "meta": {"count": len(rows)}})


# --- Sales Note Helpers -------------------------------------------------

def _append_sales_note_audit(cur: sqlite3.Cursor, sales_note_id: int, action: str, actor: str = "system", payload: Optional[dict[str, Any]] = None, ip: Optional[str] = None, ua: Optional[str] = None) -> None:
    """Append chained audit row.

    Hash chain formula: SHA256(prev_hash + '|' + id + '|' + action + '|' + payload_json_sorted)
    """
    payload_json = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True)
    prev = cur.execute(
        "SELECT hash_curr FROM sales_note_audit WHERE sales_note_id=? ORDER BY id DESC LIMIT 1",
        (sales_note_id,),
    ).fetchone()
    prev_hash = prev[0] if prev else None
    base = f"{prev_hash or ''}|{sales_note_id}|{action}|{payload_json}"
    curr_hash = hashlib.sha256(base.encode("utf-8")).hexdigest()
    cur.execute(
        "INSERT INTO sales_note_audit(sales_note_id, action, actor, ip, user_agent, payload_json, hash_prev, hash_curr) VALUES(?,?,?,?,?,?,?,?)",
        (
            sales_note_id,
            action,
            actor,
            ip,
            ua,
            payload_json,
            prev_hash,
            curr_hash,
        ),
    )


def _next_sales_note_number(cur: sqlite3.Cursor) -> str:
    """Devuelve siguiente correlativo formato NNN-YYYY (NNN zero padded)."""
    year = datetime.now(UTC).year
    row = cur.execute(
        "SELECT note_number FROM sales_notes WHERE note_number LIKE ? ORDER BY id DESC LIMIT 1",
        (f"%-{year}",),
    ).fetchone()
    if not row or not row[0]:
        seq = 1
    else:
        try:
            seq = int(row[0].split("-")[0]) + 1
        except ValueError:  # pragma: no cover
            seq = 1
    return f"{seq:03d}-{year}"


@ep_bp.post("/api/sales-notes/<int:sid>/approve")
def approve_sales_note(sid: int):
    """Aprueba una nota de venta (draft -> issued) asignando correlativo.

    Reglas:
      - Debe estar en estado 'draft'.
      - EP asociado debe seguir en estado 'submitted' o 'approved'.
      - Asigna note_number único, setea approved_at y emitted_at.
    """
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        cur = con.cursor()
        sn = cur.execute("SELECT * FROM sales_notes WHERE id=?", (sid,)).fetchone()
        if not sn:
            raise Unprocessable("sales_note_not_found", "Nota de venta inexistente", extra={"sales_note_id": sid})
        if sn["status"] != "draft":
            raise Unprocessable("invalid_state", "Solo notas en draft se pueden aprobar", extra={"status": sn["status"]})
        ep_id = sn["ep_id"]
        h = cur.execute("SELECT id, status FROM ep_headers WHERE id=?", (ep_id,)).fetchone()
        if not h:
            raise Unprocessable("ep_not_found", "EP inexistente", extra={"ep_id": ep_id})
        if h["status"] not in ("submitted", "approved"):
            raise Unprocessable("invalid_state", "EP no está en estado aprobable para nota", extra={"ep_status": h["status"]})
        note_number = _next_sales_note_number(cur)
        # Attempt update optimistic (will fail if unique constraint race)
        try:
            cur.execute(
                "UPDATE sales_notes SET note_number=?, status='issued', approved_at=datetime('now'), emitted_at=datetime('now'), updated_at=datetime('now') WHERE id=?",
                (note_number, sid),
            )
        except sqlite3.IntegrityError:
            # Reintentar con nuevo correlativo
            note_number = _next_sales_note_number(cur)
            cur.execute(
                "UPDATE sales_notes SET note_number=?, status='issued', approved_at=datetime('now'), emitted_at=datetime('now'), updated_at=datetime('now') WHERE id=?",
                (note_number, sid),
            )
        _append_sales_note_audit(cur, sid, "approve", payload={"note_number": note_number})
        con.commit()
        return jsonify({"ok": True, "sales_note_id": sid, "note_number": note_number, "status": "issued"})


@ep_bp.post("/api/sales-notes/<int:sid>/cancel")
def cancel_sales_note(sid: int):
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        cur = con.cursor()
        row = cur.execute(
            "SELECT id, ep_id, status FROM sales_notes WHERE id=?", (sid,)
        ).fetchone()
        if not row:
            raise Unprocessable(
                "sales_note_not_found",
                "Nota de venta inexistente",
                extra={"sales_note_id": sid},
            )
        if row["status"] != "issued":
            raise Unprocessable(
                "invalid_state",
                "Solo notas 'issued' se pueden cancelar",
                extra={"sales_note_id": sid, "status": row["status"]},
            )
        # Verificar que no exista factura AR (defensivo)
        inv = cur.execute(
            (
                "SELECT id FROM ar_invoices WHERE ep_id=? "
                "AND status IN ('issued','paid','cancelled','draft') LIMIT 1"
            ),
            (row["ep_id"],),
        ).fetchone()
        if inv:
            raise Unprocessable(
                "invalid_state",
                "EP ya tiene factura; no se puede cancelar nota",
                extra={"invoice_id": inv[0]},
            )
        cur.execute(
            (
                "UPDATE sales_notes SET status='cancelled', "
                "updated_at=datetime('now') WHERE id=?"
            ),
            (sid,),
        )
        con.commit()
        return jsonify({
            "ok": True,
            "sales_note_id": sid,
            "status": "cancelled",
        })


@ep_bp.post("/api/sales-notes/<int:sid>/issue-invoice")
def sales_note_issue_invoice(sid: int):
    """Emite factura AR desde una sales_note existente.

    Similar a ep_to_invoice pero marca la nota como 'invoiced'.
    """
    TAX_RATE = 0.19
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        cur = con.cursor()
        sn = cur.execute(
            "SELECT * FROM sales_notes WHERE id=?", (sid,)
        ).fetchone()
        if not sn:
            raise Unprocessable(
                "sales_note_not_found",
                "Nota de venta inexistente",
                extra={"sales_note_id": sid},
            )
        if sn["status"] not in ("issued",):
            raise Unprocessable(
                "invalid_state",
                "Sales note no está en estado emitible",
                extra={"status": sn["status"], "sales_note_id": sid},
            )
        ep_id = sn["ep_id"]
        h = cur.execute(
            "SELECT * FROM ep_headers WHERE id=?", (ep_id,)
        ).fetchone()
        if not h:
            raise Unprocessable(
                "not_found", "EP inexistente", extra={"ep_id": ep_id}
            )
        if h["status"] not in ("approved", "invoiced", "paid"):
            raise Unprocessable(
                "invalid_state",
                f"EP no está aprobado (estado: {h['status']})",
                extra={"ep_id": ep_id},
            )
        dup = cur.execute(
            (
                "SELECT id FROM ar_invoices WHERE ep_id=? "
                "AND status IN ('issued','paid','cancelled','draft') LIMIT 1"
            ),
            (ep_id,),
        ).fetchone()
        if dup:
            raise Unprocessable(
                "duplicate_invoice",
                "EP ya tiene factura emitida",
                extra={"invoice_id": dup[0], "ep_id": ep_id},
            )
        # Recalcular montos (no confiar ciegamente en snapshot)
        lines_sum = cur.execute(
            (
                "SELECT COALESCE(SUM(amount_period),0) "
                "FROM ep_lines WHERE ep_id=?"
            ),
            (ep_id,),
        ).fetchone()
        subtotal = float(lines_sum[0] or 0)
        ded_sum = cur.execute(
            "SELECT COALESCE(SUM(amount),0) FROM ep_deductions WHERE ep_id=?",
            (ep_id,),
        ).fetchone()
        deductions_total = float(ded_sum[0] or 0)
        net = max(subtotal - deductions_total, 0.0)
        if net <= 0:
            raise Unprocessable(
                "zero_amount_invoice",
                "EP no tiene monto neto para facturar",
                extra={"ep_id": ep_id},
            )
        tax = round(net * TAX_RATE, 2)
        total = round(net + tax, 2)
        # Due date por términos de pago (si contrato)
        days = 30
        customer_id = 0
        if h["contract_id"]:
            ptd = cur.execute(
                (
                    "SELECT COALESCE(payment_terms_days,30), "
                    "COALESCE(customer_id,0) FROM client_contracts WHERE id=?"
                ),
                (h["contract_id"],),
            ).fetchone()
            if ptd:
                days = int(ptd[0] or 30)
                customer_id = int(ptd[1] or 0)
        cur.execute(
            (
                "INSERT INTO ar_invoices("  # cols
                "project_id, customer_id, ep_id, invoice_number, "
                "invoice_date, due_date, amount_net, tax_amount, "
                "amount_total, status) VALUES(?,?,?,?, date('now'), "
                "date('now','+'||?||' day'), ?, ?, ?, 'issued')"
            ),
            (
                h["project_id"],
                customer_id,
                ep_id,
                None,
                days,
                net,
                tax,
                total,
            ),
        )
        inv_id = cur.lastrowid
        # Marcar nota como invoiced
        cur.execute(
            (
                "UPDATE sales_notes SET status='invoiced', "
                "updated_at=datetime('now') WHERE id=?"
            ),
            (sid,),
        )
        # Ledger retención (igual a ep_to_invoice)
        retention_amount = 0.0
        if h["retention_pct"]:
            rpct = float(h["retention_pct"] or 0)
            if rpct > 0:
                retention_amount = round(subtotal * rpct, 2)
        if retention_amount > 0:
            existing_ledger = cur.execute(
                "SELECT 1 FROM ep_retention_ledger WHERE ep_id=? LIMIT 1",
                (ep_id,),
            ).fetchone()
            if not existing_ledger:
                cur.execute(
                    (
                        "INSERT INTO ep_retention_ledger("  # cols
                        "ep_id, amount, notes) VALUES(?,?,?)"
                    ),
                    (ep_id, retention_amount, "auto ledger on invoice"),
                )
        con.commit()
        return jsonify(
            {
                "ok": True,
                "invoice_id": inv_id,
                "sales_note_id": sid,
                "amount_net": net,
                "tax_amount": tax,
                "amount_total": total,
            }
        )


# ------------------------------
# Retention Endpoints
# ------------------------------

@ep_bp.get("/api/ep/<int:ep_id>/retention")
def ep_retention_summary(ep_id: int):
    """Devuelve el ledger de retención y totales (held vs released)."""
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        if not _ep_exists(con, ep_id):
            raise Unprocessable(
                "not_found", "EP inexistente", extra={"ep_id": ep_id}
            )
        rows = con.execute(
            "SELECT id, amount, created_at, released_at, notes "
            "FROM ep_retention_ledger WHERE ep_id=? ORDER BY id",
            (ep_id,),
        ).fetchall()
        held = sum(float(r[1] or 0) for r in rows if not r[3])
        released = sum(float(r[1] or 0) for r in rows if r[3])
        return jsonify(
            {
                "ep_id": ep_id,
                "entries": [dict(r) for r in rows],
                "retention_held": round(held, 2),
                "retention_released": round(released, 2),
                "retention_outstanding": round(held, 2),
            }
        )


@ep_bp.post("/api/ep/<int:ep_id>/retention/release")
def ep_retention_release(ep_id: int):
    """Libera retención pendiente (solo liberación total soportada por ahora).

    Body JSON: { amount? } si amount distinto a total pendiente => 422.
    """
    data = request.get_json(silent=True) or {}
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        if not _ep_exists(con, ep_id):
            raise Unprocessable(
                "not_found", "EP inexistente", extra={"ep_id": ep_id}
            )
        cur = con.cursor()
        rows = cur.execute(
            "SELECT id, amount FROM ep_retention_ledger "
            "WHERE ep_id=? AND released_at IS NULL",
            (ep_id,),
        ).fetchall()
        if not rows:
            raise Unprocessable(
                "invalid_state",
                "No hay retención pendiente para liberar",
                extra={"ep_id": ep_id},
            )
        outstanding = sum(float(r[1] or 0) for r in rows)
        req_amount = data.get("amount")
        if req_amount is None:
            req_amount = outstanding
        try:
            req_amount_f = float(req_amount)
        except (TypeError, ValueError):
            raise Unprocessable("invalid_payload", "amount inválido")
        if abs(req_amount_f - outstanding) > 1e-6:
            raise Unprocessable(
                "partial_release_not_supported",
                "Solo liberación total soportada en esta versión",
                extra={"outstanding": outstanding, "attempt": req_amount_f},
            )
        # Liberar: set released_at a todas las filas pendientes
        cur.execute(
            "UPDATE ep_retention_ledger SET released_at=datetime('now') "
            "WHERE ep_id=? AND released_at IS NULL",
            (ep_id,),
        )
        con.commit()
        return jsonify({"ok": True, "released_amount": round(outstanding, 2)})


@ep_bp.post("/api/ep/<int:ep_id>/retention/release-partial")
def ep_retention_release_partial(ep_id: int):
    """Libera una parte de la retención pendiente.

    Body JSON: { amount }
    Validaciones:
      - Debe existir retención pendiente.
      - amount > 0 y <= outstanding.
      - Crea una fila negativa (release) o marca released_at proporcional?
        En este diseño simplificado: dividimos proporcionalmente liberando
        desde las filas abiertas en orden FIFO hasta cubrir el monto.
    """
    data = request.get_json(silent=True) or {}
    try:
        req_amount_raw = data.get("amount")
        try:
            # Convertir via str para evitar type warnings si viene int/decimal
            req_amount = float(str(req_amount_raw))
        except (TypeError, ValueError):
            raise Unprocessable("invalid_payload", "amount inválido")
    except (TypeError, ValueError):
        raise Unprocessable("invalid_payload", "amount inválido")
    if req_amount <= 0:
        raise Unprocessable("invalid_payload", "amount debe ser > 0")
    with db_conn(_db_path()) as con:
        _ensure_schema(con)
        if not _ep_exists(con, ep_id):
            raise Unprocessable(
                "not_found", "EP inexistente", extra={"ep_id": ep_id}
            )
        cur = con.cursor()
        rows = cur.execute(
            (
                "SELECT id, amount FROM ep_retention_ledger "
                "WHERE ep_id=? AND released_at IS NULL ORDER BY id"
            ),
            (ep_id,),
        ).fetchall()
        if not rows:
            raise Unprocessable(
                "invalid_state",
                "No hay retención pendiente para liberar",
                extra={"ep_id": ep_id},
            )
        outstanding = sum(float(r[1] or 0) for r in rows)
        if req_amount > outstanding + 1e-6:
            raise Unprocessable(
                "amount_exceeds_outstanding",
                "Amount excede retención pendiente",
                extra={"outstanding": outstanding, "attempt": req_amount},
            )
        remaining = req_amount
        # Liberar filas completas mientras quepa
        for rid, amount in [(int(r[0]), float(r[1] or 0)) for r in rows]:
            if remaining <= 1e-9:
                break
            if amount <= remaining + 1e-9:
                cur.execute(
                    (
                        "UPDATE ep_retention_ledger SET released_at="
                        "datetime('now') WHERE id=?"
                    ),
                    (rid,),
                )
                remaining -= amount
            else:
                # Split: parte liberada -> fila released; resto pendiente
                release_amt = remaining
                leftover = amount - release_amt
                # Update original row to leftover (still pending)
                cur.execute(
                    "UPDATE ep_retention_ledger SET amount=? WHERE id=?",
                    (leftover, rid),
                )
                # Insert released row with release_amt
                cur.execute(
                    (
                        "INSERT INTO ep_retention_ledger("
                        "ep_id, amount, released_at, notes) "
                        "VALUES(?,?, datetime('now'), ?)"
                    ),
                    (ep_id, release_amt, "partial release"),
                )
                remaining = 0.0
                break
        con.commit()
        return jsonify({
            "ok": True,
            "released_amount": round(req_amount - remaining, 2),
            "outstanding_before": round(outstanding, 2),
            "outstanding_after": round(
                outstanding - (req_amount - remaining), 2
            ),
        })
