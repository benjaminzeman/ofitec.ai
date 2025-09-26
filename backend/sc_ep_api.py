"""
Blueprint SC EP (Estados de Pago de Subcontratistas).

Estructura paralela a EP cliente, enfocada en ingreso manual/importación
para control de avance y cálculo de neto después de deducciones.

Tablas: sc_ep_headers, sc_ep_lines, sc_ep_deductions, sc_ep_files (opcional)
Endpoints principales:
- POST /api/sc/ep                      (crear header)
- GET  /api/sc/ep/<id>                 (header + lines + deductions)
- PUT  /api/sc/ep/<id>                 (actualizar header editable)
- POST /api/sc/ep/<id>/lines/bulk      (reemplazar líneas)
- POST /api/sc/ep/<id>/deductions/bulk (reemplazar deducciones)
- GET  /api/sc/ep/<id>/summary         (resumen calculado)
- POST /api/sc/ep/import               (crear con header+lines+deductions)
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from flask import Blueprint, jsonify, request

try:
    from tools.common_db import (  # type: ignore
        existing_db_path,
        default_db_path,
    )
except ImportError:  # pragma: no cover
    existing_db_path = None  # type: ignore
    default_db_path = None  # type: ignore


sc_ep_bp = Blueprint("sc_ep", __name__)


def _db_path() -> str:
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


def db() -> sqlite3.Connection:
    con = sqlite3.connect(_db_path())
    con.row_factory = sqlite3.Row
    return con


def _ensure_schema(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS sc_ep_headers (
          id INTEGER PRIMARY KEY,
          project_id INTEGER NOT NULL,
          subcontract_id INTEGER,
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
            CREATE INDEX IF NOT EXISTS idx_sc_ep_project
                ON sc_ep_headers(project_id);
            CREATE INDEX IF NOT EXISTS idx_sc_ep_status
                ON sc_ep_headers(status);

        CREATE TABLE IF NOT EXISTS sc_ep_lines (
          id INTEGER PRIMARY KEY,
          ep_id INTEGER NOT NULL,
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
        CREATE INDEX IF NOT EXISTS idx_sc_ep_lines_ep ON sc_ep_lines(ep_id);

        CREATE TABLE IF NOT EXISTS sc_ep_deductions (
          id INTEGER PRIMARY KEY,
          ep_id INTEGER NOT NULL,
          type TEXT CHECK (
              type IN ('retention','advance_amortization','penalty','other')
          ),
          description TEXT,
          amount REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sc_ep_ded_ep ON sc_ep_deductions(ep_id);

        CREATE TABLE IF NOT EXISTS sc_ep_files (
          id INTEGER PRIMARY KEY,
          ep_id INTEGER NOT NULL,
          drive_file_id TEXT,
          storage_url TEXT,
          kind TEXT CHECK (kind IN ('xlsx','pdf')),
          uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    con.commit()


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


@sc_ep_bp.errorhandler(Unprocessable)
def _unprocessable(e: Unprocessable):
    return jsonify(e.to_payload()), 422


# Helpers

def _ep_exists(con: sqlite3.Connection, ep_id: int) -> bool:
    row = con.execute(
        "SELECT 1 FROM sc_ep_headers WHERE id=?",
        (ep_id,),
    ).fetchone()
    return row is not None


def _lines_subtotal(con: sqlite3.Connection, ep_id: int) -> float:
    row = con.execute(
        "SELECT COALESCE(SUM(amount_period),0) FROM sc_ep_lines WHERE ep_id=?",
        (ep_id,),
    ).fetchone()
    return float(row[0] or 0)


def _summary(con: sqlite3.Connection, ep_id: int) -> dict:
    h = con.execute(
        "SELECT * FROM sc_ep_headers WHERE id=?",
        (ep_id,),
    ).fetchone()
    if not h:
        raise Unprocessable(
            "not_found",
            "SC EP inexistente",
            extra={"ep_id": ep_id},
        )
    subtotal = _lines_subtotal(con, ep_id)
    cur = con.execute(
        (
            "SELECT type, COALESCE(SUM(amount),0) FROM sc_ep_deductions "
            "WHERE ep_id=? GROUP BY type"
        ),
        (ep_id,),
    )
    ded_by_type = {str(t or "other"): float(v or 0) for t, v in cur.fetchall()}
    total_ded = sum(ded_by_type.values())
    retention_pct = float(h["retention_pct"] or 0)
    retention_computed = 0.0
    if "retention" not in ded_by_type and retention_pct > 0:
        retention_computed = round(subtotal * retention_pct, 2)
    net = max(round(subtotal - total_ded, 2), 0.0)
    return {
        "ep": dict(h),
        "lines_subtotal": round(subtotal, 2),
        "deductions": {k: round(v, 2) for k, v in ded_by_type.items()},
        "deductions_total": round(total_ded, 2),
        "retention_computed": retention_computed or None,
        "amount_net": net,
    }


# Endpoints

@sc_ep_bp.get("/api/sc/ep")
def list_sc_eps():
    """Listado de EP de subcontrato con filtros opcionales y totales.

    Query params opcionales:
      - project_id: int
      - status: str
      - limit: int (por defecto 500)
    """
    project_id = request.args.get("project_id")
    status = request.args.get("status")
    try:
        limit = int(request.args.get("limit", "500"))
    except (TypeError, ValueError):
        limit = 500

    con = db()
    try:
        _ensure_schema(con)
        where: list[str] = ["1=1"]
        params: list = []
        if project_id:
            try:
                params.append(int(project_id))
                where.append("h.project_id = ?")
            except (TypeError, ValueError) as exc:
                raise Unprocessable(
                    "invalid_param",
                    "project_id inválido",
                ) from exc
        if status:
            params.append(status)
            where.append("h.status = ?")
        q = (
            "SELECT h.*, "
            "  (SELECT COALESCE(SUM(l.amount_period),0) "
            "     FROM sc_ep_lines l WHERE l.ep_id = h.id) AS lines_subtotal, "
            "  (SELECT COALESCE(SUM(d.amount),0) "
            "     FROM sc_ep_deductions d "
            "     WHERE d.ep_id = h.id) AS deductions_total "
            "FROM sc_ep_headers h "
            "WHERE "
            + " AND ".join(where)
            + " ORDER BY h.id DESC LIMIT ?"
        )
        params.append(limit)
        rows = [dict(r) for r in con.execute(q, params).fetchall()]
        # Calcular neto sugerido aplicando retención si no viene como deducción
        for r in rows:
            subtotal = float(r.get("lines_subtotal") or 0)
            ded = float(r.get("deductions_total") or 0)
            # Nota: la retención puede ya estar como deducción explícita.
            # Aquí solo entregamos fields base.
            r["amount_net_estimate"] = max(round(subtotal - ded, 2), 0.0)
        return jsonify({"items": rows})
    finally:
        con.close()


@sc_ep_bp.get("/api/sc/ping")
def sc_ping():
    return jsonify({"ok": True, "module": "sc_ep"})


@sc_ep_bp.post("/api/sc/ep")
def create_sc_ep():
    data = request.get_json(force=True) or {}
    if not data.get("project_id"):
        raise Unprocessable("invalid_payload", "project_id requerido")
    con = db()
    try:
        _ensure_schema(con)
        cur = con.cursor()
        cur.execute(
            (
                "INSERT INTO sc_ep_headers("
                "project_id, subcontract_id, ep_number, period_start, "
                "period_end, submitted_at, status, retention_pct, notes) "
                "VALUES(?,?,?,?,?, "
                "COALESCE(?, date('now')), 'submitted', ?, ?)"
            ),
            (
                int(data["project_id"]),
                data.get("subcontract_id"),
                data.get("ep_number"),
                data.get("period_start"),
                data.get("period_end"),
                data.get("submitted_at"),
                data.get("retention_pct"),
                data.get("notes"),
            ),
        )
        ep_id = cur.lastrowid
        con.commit()
        return jsonify({"ok": True, "ep_id": ep_id}), 201
    finally:
        con.close()


@sc_ep_bp.get("/api/sc/ep/<int:ep_id>")
def get_sc_ep(ep_id: int):
    con = db()
    try:
        _ensure_schema(con)
        if not _ep_exists(con, ep_id):
            raise Unprocessable(
                "not_found",
                "SC EP inexistente",
                extra={"ep_id": ep_id},
            )
        h = con.execute(
            "SELECT * FROM sc_ep_headers WHERE id=?",
            (ep_id,),
        ).fetchone()
        lines = [
            dict(r)
            for r in con.execute(
                "SELECT * FROM sc_ep_lines WHERE ep_id=? ORDER BY id",
                (ep_id,),
            ).fetchall()
        ]
        deductions = [
            dict(r)
            for r in con.execute(
                "SELECT * FROM sc_ep_deductions WHERE ep_id=? ORDER BY id",
                (ep_id,),
            ).fetchall()
        ]
        return jsonify(
            {"header": dict(h), "lines": lines, "deductions": deductions}
        )
    finally:
        con.close()


@sc_ep_bp.put("/api/sc/ep/<int:ep_id>")
def update_sc_ep(ep_id: int):
    data = request.get_json(force=True) or {}
    con = db()
    try:
        _ensure_schema(con)
        if not _ep_exists(con, ep_id):
            raise Unprocessable(
                "not_found",
                "SC EP inexistente",
                extra={"ep_id": ep_id},
            )
        allowed = {
            "ep_number",
            "period_start",
            "period_end",
            "submitted_at",
            "approved_at",
            "status",
            "retention_pct",
            "notes",
            "subcontract_id",
        }
        sets: list[str] = []
        params: list = []
        for k, v in data.items():
            if k in allowed:
                sets.append(f"{k} = ?")
                params.append(v)
        if not sets:
            return jsonify({"ok": True, "updated": 0})
        params.append(ep_id)
        con.execute(
            "UPDATE sc_ep_headers SET " + ", ".join(sets) + " WHERE id=?",
            params,
        )
        con.commit()
        return jsonify({"ok": True, "updated": len(sets)})
    finally:
        con.close()


@sc_ep_bp.post("/api/sc/ep/<int:ep_id>/lines/bulk")
def set_sc_ep_lines(ep_id: int):
    payload = request.get_json(force=True) or {}
    lines = payload.get("lines") or []
    if not isinstance(lines, list):
        raise Unprocessable("invalid_payload", "lines debe ser lista")
    con = db()
    try:
        _ensure_schema(con)
        if not _ep_exists(con, ep_id):
            raise Unprocessable(
                "not_found",
                "SC EP inexistente",
                extra={"ep_id": ep_id},
            )
        cur = con.cursor()
        cur.execute("DELETE FROM sc_ep_lines WHERE ep_id=?", (ep_id,))
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
            cur.execute(
                (
                    "INSERT INTO sc_ep_lines("
                    "ep_id, item_code, description, unit, qty_period, "
                    "unit_price, amount_period, qty_cum, amount_cum, chapter) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?)"
                ),
                (
                    ep_id,
                    ln.get("item_code"),
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
    finally:
        con.close()


@sc_ep_bp.post("/api/sc/ep/<int:ep_id>/deductions/bulk")
def set_sc_ep_deductions(ep_id: int):
    payload = request.get_json(force=True) or {}
    deductions = payload.get("deductions") or []
    if not isinstance(deductions, list):
        raise Unprocessable("invalid_payload", "deductions debe ser lista")
    con = db()
    try:
        _ensure_schema(con)
        if not _ep_exists(con, ep_id):
            raise Unprocessable(
                "not_found",
                "SC EP inexistente",
                extra={"ep_id": ep_id},
            )
        cur = con.cursor()
        cur.execute("DELETE FROM sc_ep_deductions WHERE ep_id=?", (ep_id,))
        for d in deductions:
            cur.execute(
                (
                    "INSERT INTO sc_ep_deductions("
                    "ep_id, type, description, amount) VALUES(?,?,?,?)"
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
    finally:
        con.close()


@sc_ep_bp.get("/api/sc/ep/<int:ep_id>/summary")
def sc_ep_summary(ep_id: int):
    con = db()
    try:
        _ensure_schema(con)
        if not _ep_exists(con, ep_id):
            raise Unprocessable(
                "not_found",
                "SC EP inexistente",
                extra={"ep_id": ep_id},
            )
        return jsonify(_summary(con, ep_id))
    finally:
        con.close()


@sc_ep_bp.post("/api/sc/ep/import")
def import_sc_ep():
    data = request.get_json(force=True) or {}
    header = data.get("header")
    lines = data.get("lines", [])
    deductions = data.get("deductions", [])
    if not header or not lines:
        raise Unprocessable("invalid_payload", "header or lines missing")
    con = db()
    try:
        _ensure_schema(con)
        cur = con.cursor()
        cur.execute(
            (
                "INSERT INTO sc_ep_headers("
                "project_id, subcontract_id, ep_number, period_start, "
                "period_end, "
                "submitted_at, status, retention_pct, notes) "
                "VALUES(?,?,?,?,?, "
                "COALESCE(?, date('now')), 'submitted', ?, ?)"
            ),
            (
                int(header["project_id"]),
                header.get("subcontract_id"),
                header.get("ep_number"),
                header.get("period_start"),
                header.get("period_end"),
                header.get("submitted_at"),
                header.get("retention_pct"),
                header.get("notes"),
            ),
        )
        ep_id = cur.lastrowid
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
            cur.execute(
                (
                    "INSERT INTO sc_ep_lines("
                    "ep_id, item_code, description, unit, qty_period, "
                    "unit_price, amount_period, qty_cum, amount_cum, chapter) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?)"
                ),
                (
                    ep_id,
                    ln.get("item_code"),
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
                    "INSERT INTO sc_ep_deductions("
                    "ep_id, type, description, amount) VALUES(?,?,?,?)"
                ),
                (
                    ep_id,
                    d.get("type"),
                    d.get("description"),
                    d.get("amount"),
                ),
            )
        con.commit()
        return jsonify({"ok": True, "ep_id": ep_id})
    finally:
        con.close()
