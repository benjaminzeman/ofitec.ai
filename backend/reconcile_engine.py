"""Hybrid reconciliation helpers (rules + fuzzy) with evidences for suggestions."""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, List, Optional

from rapidfuzz import fuzz


@dataclass
class Movement:
    id: int
    amount: float
    currency: str
    date: Optional[datetime]
    vendor_name: str
    reference: str
    raw: dict[str, Any]


@dataclass
class Candidate:
    id: int
    kind: str  # 'ap', 'ar', 'expense', 'payroll', 'tax'
    amount: float
    currency: str
    date: Optional[datetime]
    vendor_name: str
    vendor_rut: str | None
    reference: str | None
    raw: dict[str, Any]


@dataclass
class Evidence:
    rule: str
    detail: str
    score: float | None = None


@dataclass
class Suggestion:
    movement_id: int
    candidate_id: int
    candidate_kind: str
    confidence: float
    evidences: list[Evidence]

    def as_dict(self) -> dict[str, Any]:
        return {
            "movement_id": self.movement_id,
            "candidate_id": self.candidate_id,
            "candidate_kind": self.candidate_kind,
            "confidence": round(self.confidence, 4),
            "evidence": [
                {
                    "rule": ev.rule,
                    "detail": ev.detail,
                    "score": None if ev.score is None else round(ev.score, 4),
                }
                for ev in self.evidences
            ],
        }


_AMOUNT_TOLERANCE = 0.03  # 3%
_DATE_TOLERANCE_DAYS = 7
_VENDOR_THRESHOLD = 70


def _parse_date(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[: len(fmt)], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _normalize_name(name: str | None) -> str:
    if not name:
        return ""
    return " ".join(name.strip().lower().replace("ñ", "n").split())


def _amount_similarity(base: float, other: float) -> float:
    if base == 0:
        return 0.0
    diff = abs(abs(base) - abs(other))
    rel = diff / max(abs(base), 1.0)
    return max(0.0, 1.0 - rel)


def _date_similarity(base: Optional[datetime], other: Optional[datetime]) -> float:
    if not base or not other:
        return 0.0
    days = abs((base.date() - other.date()).days)
    if days > 30:
        return 0.0
    return max(0.0, 1.0 - (days / _DATE_TOLERANCE_DAYS))


def _vendor_score(base_name: str, candidate_name: str) -> float:
    if not base_name or not candidate_name:
        return 0.0
    score = fuzz.WRatio(base_name, candidate_name)
    return score / 100.0


def _collect_movement(row: sqlite3.Row) -> Movement:
    return Movement(
        id=row["id"],
        amount=float(row["monto"] or 0),
        currency=(row["moneda"] or "CLP"),
        date=_parse_date(row.get("fecha")),
        vendor_name=row.get("glosa") or row.get("referencia") or "",
        reference=row.get("referencia") or row.get("glosa") or "",
        raw=dict(row),
    )


def _collect_candidate(kind: str, row: sqlite3.Row) -> Candidate:
    return Candidate(
        id=row["id"],
        kind=kind,
        amount=float(row.get("monto") or row.get("total_amount") or 0),
        currency=row.get("moneda") or row.get("currency") or "CLP",
        date=_parse_date(row.get("fecha") or row.get("invoice_date") or row.get("periodo")),
        vendor_name=row.get("proveedor") or row.get("vendor_name") or row.get("customer_name") or "",
        vendor_rut=row.get("proveedor_rut") or row.get("vendor_rut") or row.get("customer_rut"),
        reference=row.get("invoice_number") or row.get("documento") or row.get("ref") or None,
        raw=dict(row),
    )


def fetch_bank_movement(conn: sqlite3.Connection, movement_id: int) -> Movement | None:
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, fecha, glosa, referencia, monto, moneda FROM bank_movements WHERE id=?",
        (movement_id,),
    ).fetchone()
    if not row:
        return None
    return _collect_movement(row)


def fetch_candidates(
    conn: sqlite3.Connection,
    movement: Movement,
    amount_tolerance: float = _AMOUNT_TOLERANCE,
) -> list[Candidate]:
    lower = abs(movement.amount) * (1 - amount_tolerance)
    upper = abs(movement.amount) * (1 + amount_tolerance)
    conn.row_factory = sqlite3.Row
    candidates: list[Candidate] = []
    for kind, sql in [
        (
            "ap",
            "SELECT id, invoice_date, total_amount, vendor_name, vendor_rut, invoice_number FROM ap_invoices "
            "WHERE ABS(total_amount) BETWEEN ? AND ?",
        ),
        (
            "ar",
            "SELECT id, invoice_date, total_amount, customer_name AS vendor_name, customer_rut AS vendor_rut, invoice_number "
            "FROM sales_invoices WHERE ABS(total_amount) BETWEEN ? AND ?",
        ),
        (
            "expense",
            "SELECT id, fecha, monto, proveedor_rut, proveedor_rut AS vendor_rut, descripcion AS proveedor, descripcion FROM expenses "
            "WHERE ABS(monto) BETWEEN ? AND ?",
        ),
    ]:
        for row in conn.execute(sql, (lower, upper)):
            candidates.append(_collect_candidate(kind, row))
    return candidates


def score_candidate(movement: Movement, candidate: Candidate) -> Suggestion:
    evidences: list[Evidence] = []
    base_name = _normalize_name(movement.vendor_name)
    candidate_name = _normalize_name(candidate.vendor_name)

    amount_score = _amount_similarity(movement.amount, candidate.amount)
    evidences.append(Evidence("amount", f"diff={abs(abs(movement.amount) - abs(candidate.amount)):.2f}", amount_score))

    date_score = _date_similarity(movement.date, candidate.date)
    evidences.append(
        Evidence(
            "date",
            f"movement={movement.date.date() if movement.date else 'n/a'} candidate={candidate.date.date() if candidate.date else 'n/a'}",
            date_score,
        )
    )

    vendor_score = _vendor_score(base_name, candidate_name)
    evidences.append(Evidence("vendor", f"similarity={vendor_score:.2f}", vendor_score))

    confidence = (0.5 * amount_score) + (0.3 * vendor_score) + (0.2 * date_score)
    match_type = "rule" if amount_score > 0.98 and vendor_score > 0.9 and date_score > 0.8 else "fuzzy"
    evidences.append(Evidence("match_type", match_type))

    return Suggestion(
        movement_id=movement.id,
        candidate_id=candidate.id,
        candidate_kind=candidate.kind,
        confidence=confidence,
        evidences=evidences,
    )


def suggest_for_movement(
    conn: sqlite3.Connection,
    movement_id: int,
    *,
    amount_tolerance: float = _AMOUNT_TOLERANCE,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    movement = fetch_bank_movement(conn, movement_id)
    if not movement:
        return []
    candidates = fetch_candidates(conn, movement, amount_tolerance=amount_tolerance)
    if not candidates:
        return []
    suggestions = [score_candidate(movement, cand) for cand in candidates]
    suggestions.sort(key=lambda s: s.confidence, reverse=True)
    return [s.as_dict() for s in suggestions[:top_n]]
