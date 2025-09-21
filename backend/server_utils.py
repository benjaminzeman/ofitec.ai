"""Pure helper utilities extracted from server.py for easier testing.

These functions intentionally avoid importing the large application context.
"""
from __future__ import annotations

from typing import List, Dict, Any
import sqlite3


def list_routes(app) -> List[Dict[str, Any]]:  # type: ignore[reportAny]
    """Return a list of route metadata (rule, endpoint, methods).

    Filters out HEAD/OPTIONS which Flask adds automatically.
    """
    out: List[Dict[str, Any]] = []
    try:
        rules = list(app.url_map.iter_rules())  # type: ignore[attr-defined]
    except AttributeError:  # pragma: no cover - defensive
        return out
    for r in rules:
        methods = sorted(
            m
            for m in getattr(r, 'methods', [])
            if m not in {"HEAD", "OPTIONS"}
        )
        out.append({
            'rule': str(getattr(r, 'rule', '')),
            'endpoint': getattr(r, 'endpoint', ''),
            'methods': methods,
        })
    out.sort(key=lambda x: x['rule'])
    return out


def table_exists(con: sqlite3.Connection, name: str) -> bool:
    """Return True if the connection exposes a table or view named `name`."""
    cur = con.cursor()
    try:
        cur.execute(
            (
                "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') "
                "AND name=? LIMIT 1"
            ),
            (name,),
        )
        return cur.fetchone() is not None
    except sqlite3.Error:  # pragma: no cover - defensive
        return False


def list_db_objects(con: sqlite3.Connection) -> List[Dict[str, str]]:
    """Return SQLite tables/views metadata as a list of name/type dicts."""
    cur = con.cursor()
    rows: List[Dict[str, str]] = []
    try:
        cur.execute(
            (
                "SELECT name, type FROM sqlite_master "
                "WHERE type IN ('table','view') ORDER BY type, name"
            )
        )
        for name, typ in cur.fetchall():
            rows.append({'name': name, 'type': typ})
    except sqlite3.Error:  # pragma: no cover
        return []
    return rows


NULL_EQUIVALENTS = {None, '', 'null', 'NULL'}


def normalize_project_name(raw: str | None) -> str | None:
    """Normalize project aliases by trimming and filtering null-like values."""
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    if s in NULL_EQUIVALENTS:
        return None
    return s
