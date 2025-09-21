import os
import sqlite3
from pathlib import Path

import pytest

from backend import db_utils


def test_resolve_db_path_default(monkeypatch):
    monkeypatch.delenv("DB_PATH", raising=False)
    path = db_utils.resolve_db_path_for_tests()
    assert path.replace("/", os.sep).endswith(os.path.join("data", "chipax_data.db"))


def test_resolve_db_path_absolute(monkeypatch, tmp_path):
    custom = tmp_path / "abs.db"
    custom.write_text("")
    monkeypatch.setenv("DB_PATH", str(custom))
    path = db_utils.resolve_db_path_for_tests()
    assert path == str(custom)


def test_resolve_db_path_relative(monkeypatch):
    rel = os.path.join("data", "custom_rel.db")
    monkeypatch.setenv("DB_PATH", rel)
    path = db_utils.resolve_db_path_for_tests()
    repo_root = Path(db_utils.__file__).resolve().parent.parent
    expected = repo_root / rel
    assert path == str(expected)


def test_db_conn_context_manager_closes(tmp_path):
    db_file = tmp_path / "ctx.db"
    with db_utils.db_conn(str(db_file)) as con:
        con.execute("CREATE TABLE t(id INTEGER)")
        con.execute("INSERT INTO t(id) VALUES (1)")
        assert con.row_factory is not None
    with pytest.raises(sqlite3.ProgrammingError):
        con.execute("SELECT 1")

