#!/usr/bin/env python3
"""
Ofitec sequential numbering utilities (SQLite).

Provides an atomic counter per sequence name with prefix and padding.

Tables:
- ofitec_sequences(name PRIMARY KEY, prefix TEXT, padding INT, next_value INT NOT NULL, enable_manual INT, updated_at TEXT)

Usage example:
    conn = sqlite3.connect(db)
    ensure_sequence(conn, 'po_number', prefix='PO-', padding=5, start=1)
    num = next_number(conn, 'po_number')  # => 'PO-00001'
"""

from __future__ import annotations

import sqlite3
from typing import Optional


def ensure_sequence(
    conn: sqlite3.Connection,
    name: str,
    *,
    prefix: Optional[str] = None,
    padding: Optional[int] = None,
    start: Optional[int] = None,
    enable_manual: Optional[bool] = None,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ofitec_sequences (
          name TEXT PRIMARY KEY,
          prefix TEXT,
          padding INTEGER DEFAULT 0,
          next_value INTEGER NOT NULL,
          enable_manual INTEGER DEFAULT 1,
          updated_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    cur = conn.execute("SELECT name FROM ofitec_sequences WHERE name = ?", (name,))
    if cur.fetchone() is None:
        nv = start if (start is not None and start > 0) else 1
        conn.execute(
            "INSERT INTO ofitec_sequences(name, prefix, padding, next_value, enable_manual) VALUES(?,?,?,?,?)",
            (name, prefix or "", int(padding or 0), int(nv), 1 if (enable_manual is None or enable_manual) else 0),
        )
    else:
        parts, params = [], []
        if prefix is not None:
            parts.append("prefix = ?"); params.append(prefix)
        if padding is not None:
            parts.append("padding = ?"); params.append(int(padding))
        if start is not None and start > 0:
            parts.append("next_value = ?"); params.append(int(start))
        if enable_manual is not None:
            parts.append("enable_manual = ?"); params.append(1 if enable_manual else 0)
        if parts:
            parts.append("updated_at = datetime('now')")
            sql = "UPDATE ofitec_sequences SET " + ", ".join(parts) + " WHERE name = ?"
            params.append(name)
            conn.execute(sql, params)


def _format(prefix: str, padding: int, value: int) -> str:
    if padding and padding > 0:
        return f"{prefix or ''}{value:0{padding}d}"
    return f"{prefix or ''}{value}"


def next_number(conn: sqlite3.Connection, name: str) -> str:
    """Atomically get the next formatted number for a sequence and increment it."""
    cur = conn.execute("SELECT prefix, padding, next_value FROM ofitec_sequences WHERE name = ?", (name,))
    row = cur.fetchone()
    if row is None:
        # Initialize default sequence
        ensure_sequence(conn, name)
        cur = conn.execute("SELECT prefix, padding, next_value FROM ofitec_sequences WHERE name = ?", (name,))
        row = cur.fetchone()
    prefix, padding, next_value = row[0] or "", int(row[1] or 0), int(row[2])
    num = _format(prefix, padding, next_value)
    conn.execute(
        "UPDATE ofitec_sequences SET next_value = ?, updated_at = datetime('now') WHERE name = ?",
        (next_value + 1, name),
    )
    return num


def peek_number(conn: sqlite3.Connection, name: str) -> str:
    cur = conn.execute("SELECT prefix, padding, next_value FROM ofitec_sequences WHERE name = ?", (name,))
    row = cur.fetchone()
    if row is None:
        return _format("", 0, 1)
    return _format(row[0] or "", int(row[1] or 0), int(row[2]))

