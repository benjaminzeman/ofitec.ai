"""Shared lightweight DB utilities.

Provides a context manager `db_conn()` that returns a connection with
`row_factory=sqlite3.Row`. DB path is resolved from the DB_PATH env var
or falls back to data/chipax_data.db. Centralizing this helps ensure
connections are always closed (eliminating ResourceWarning noise).
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, UTC
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def _resolve_db_path() -> str:
    raw = os.getenv("DB_PATH")
    if raw:
        p = Path(raw)
        if not p.is_absolute():
            p = Path(__file__).resolve().parent.parent / p
        return str(p)
    base = Path(__file__).resolve().parent.parent
    return str(base / "data" / "chipax_data.db")

    
def resolve_db_path_for_tests() -> str:  # pragma: no cover - thin wrapper
    return _resolve_db_path()


_DT_FORMAT = "%Y-%m-%dT%H:%M:%S"  # second precision


def _adapt_datetime(val: datetime) -> str:  # pragma: no cover - deterministic
    if val.tzinfo is None:
        # Assume naive datetimes are UTC input; make explicit for storage semantics
        val = val.replace(tzinfo=UTC)
    return val.astimezone(UTC).strftime(_DT_FORMAT)


def _convert_datetime(raw: bytes) -> datetime:  # pragma: no cover - deterministic
    try:
        txt = raw.decode("utf-8")
        return datetime.strptime(txt, _DT_FORMAT).replace(tzinfo=UTC)
    except Exception:
        # Fallback to now to avoid crashes in legacy rows
        return datetime.now(UTC)


# Register adapters only once
try:  # pragma: no cover - idempotent
    sqlite3.register_adapter(datetime, _adapt_datetime)
    sqlite3.register_converter("TIMESTAMP", _convert_datetime)
except Exception:  # pragma: no cover
    pass


@contextmanager
def db_conn(path: str | None = None) -> Iterator[sqlite3.Connection]:
    con = sqlite3.connect(path or _resolve_db_path(), detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        con.row_factory = sqlite3.Row
        yield con
    finally:
        try:
            con.close()
        except sqlite3.Error:  # pragma: no cover - defensive narrow
            pass
