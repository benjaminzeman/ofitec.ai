from datetime import datetime, UTC

from backend.db_utils import db_conn


def test_datetime_adapter_round_trip(tmp_path, monkeypatch):
    # Force separate temp DB
    monkeypatch.setenv('DB_PATH', str(tmp_path / 'adapter.db'))
    now = datetime(2025, 9, 20, 12, 34, 56, tzinfo=UTC)
    with db_conn() as con:
        con.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, created_at TIMESTAMP)")
        con.execute("INSERT INTO sample(created_at) VALUES (?)", (now,))
        row = con.execute("SELECT created_at FROM sample").fetchone()
        fetched = row["created_at"]
    assert isinstance(fetched, datetime)
    assert fetched.tzinfo == UTC
    # Stored with second precision (microseconds trimmed)
    assert fetched == now.replace(microsecond=0)
    # Inserting naive datetime is coerced to UTC
    naive = datetime(2025, 9, 20, 1, 2, 3)
    with db_conn() as con:
        con.execute("INSERT INTO sample(created_at) VALUES (?)", (naive,))
        rows = con.execute("SELECT created_at FROM sample ORDER BY id DESC LIMIT 1").fetchall()
        last = rows[0]["created_at"]
    assert last.tzinfo == UTC
    # The naive original interpreted as UTC should match its own fields
    assert last.hour == 1 and last.minute == 2 and last.second == 3
