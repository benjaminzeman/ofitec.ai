"""Legacy compatibility helpers for conciliacion endpoints.

This module centralizes behaviors required by legacy tests so the clean API
(`conciliacion_api_clean.py`) can delegate without embedding sprawling logic.

Responsibilities:
- Table bootstrap for recon_reconciliations, recon_links, recon_aliases and reference tables.
- Combined link insertion when bank+sales provided separately.
- Negative amount normalization.
- Alias truncation + violation counting callback.

The public functions here are intentionally small wrappers used by the clean
blueprint. They return plain dicts or scalar IDs so they are easy to test.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from db_utils import db_conn

ALIAS_MAX_LEN = 120

def truncate_alias(value: str) -> Tuple[str, bool]:
    if not value:
        return "", False
    if len(value) <= ALIAS_MAX_LEN:
        return value, False
    return value[:ALIAS_MAX_LEN], True

REF_TABLE_DDL = [
    "CREATE TABLE IF NOT EXISTS sales_invoices(id INTEGER PRIMARY KEY, invoice_number TEXT, invoice_date TEXT)",
    "CREATE TABLE IF NOT EXISTS bank_movements(id INTEGER PRIMARY KEY, referencia TEXT, glosa TEXT, fecha TEXT)",
    "CREATE TABLE IF NOT EXISTS ap_invoices(id INTEGER PRIMARY KEY, invoice_number TEXT, invoice_date TEXT)",
    "CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY, descripcion TEXT, fecha TEXT)",
    "CREATE TABLE IF NOT EXISTS taxes(id INTEGER PRIMARY KEY, tipo TEXT, periodo TEXT)",
    "CREATE TABLE IF NOT EXISTS payroll_slips(id INTEGER PRIMARY KEY, periodo TEXT, rut_trabajador TEXT)",
]

RECON_DDL = [
    """
    CREATE TABLE IF NOT EXISTS recon_reconciliations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        context TEXT,
        confidence REAL,
        movement_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS recon_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reconciliation_id INTEGER,
        bank_movement_id INTEGER,
        sales_invoice_id INTEGER,
        purchase_invoice_id INTEGER,
        expense_id INTEGER,
        payroll_id INTEGER,
        tax_id INTEGER,
        amount REAL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS recon_aliases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alias TEXT UNIQUE NOT NULL,
        canonical TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


def bootstrap_tables(include_alias: bool) -> None:
    with db_conn() as conn:
        for ddl in REF_TABLE_DDL:
            conn.execute(ddl)
        for ddl in RECON_DDL[:2]:  # reconciliations + links
            conn.execute(ddl)
        if include_alias:
            conn.execute(RECON_DDL[2])
        conn.commit()


def normalize_links(raw_links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for l in raw_links:
        c = dict(l)
        try:
            amt = c.get("amount")
            if isinstance(amt, (int, float)) and amt < 0:
                c["amount"] = 0
        except Exception:
            c["amount"] = 0
        out.append(c)
    return out


def insert_reconciliation(context: str, confidence: Optional[float], movement_id: Optional[int] = None) -> int:
    with db_conn() as conn:
        # Detect legacy schema missing movement_id column
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(recon_reconciliations)").fetchall()]
        except Exception:
            cols = []
        if 'movement_id' not in cols:
            cur = conn.execute(
                "INSERT INTO recon_reconciliations(context, confidence) VALUES (?,?)",
                (context, confidence),
            )
        else:
            cur = conn.execute(
                "INSERT INTO recon_reconciliations(context, confidence, movement_id) VALUES (?,?,?)",
                (context, confidence, movement_id),
            )
        conn.commit()
        return cur.lastrowid


def insert_links(recon_id: int, links: List[Dict[str, Any]]) -> int:
    inserted = 0
    with db_conn() as conn:
        for l in links:
            conn.execute(
                (
                    "INSERT INTO recon_links("
                    "reconciliation_id, bank_movement_id, sales_invoice_id, purchase_invoice_id, "
                    "expense_id, payroll_id, tax_id, amount) VALUES (?,?,?,?,?,?,?,?)"
                ),
                (
                    recon_id,
                    l.get("bank_movement_id"),
                    l.get("sales_invoice_id"),
                    l.get("purchase_invoice_id"),
                    l.get("expense_id"),
                    l.get("payroll_id"),
                    l.get("tax_id"),
                    l.get("amount"),
                ),
            )
            inserted += 1
        conn.commit()
    return inserted


def maybe_insert_combined_row(recon_id: int, links: List[Dict[str, Any]]) -> bool:
    bank_id = None
    sales_id = None
    total = 0.0
    for l in links:
        if bank_id is None and l.get("bank_movement_id") is not None:
            bank_id = l.get("bank_movement_id")
        if sales_id is None and l.get("sales_invoice_id") is not None:
            sales_id = l.get("sales_invoice_id")
        try:
            a = l.get("amount")
            if isinstance(a, (int,float)):
                total += float(a)
        except Exception:
            pass
    if bank_id is not None and sales_id is not None:
        with db_conn() as conn:
            conn.execute(
                (
                    "INSERT INTO recon_links("
                    "reconciliation_id, bank_movement_id, sales_invoice_id, purchase_invoice_id, "
                    "expense_id, payroll_id, tax_id, amount) VALUES (?,?,?,?,?,?,?,?)"
                ),
                (recon_id, bank_id, sales_id, None, None, None, None, total),
            )
            conn.commit()
        return True
    return False


def upsert_alias(alias: str, canonical: str) -> None:
    with db_conn() as conn:
        conn.execute(
            """
            INSERT INTO recon_aliases(alias, canonical)
            VALUES(?, ?)
            ON CONFLICT(alias) DO UPDATE SET
              canonical=excluded.canonical,
              updated_at=CURRENT_TIMESTAMP
            """,
            (alias, canonical or alias),
        )
        conn.commit()
