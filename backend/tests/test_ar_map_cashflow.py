import os
import sqlite3
from pathlib import Path
import uuid

import pytest
from backend import server


@pytest.fixture(name="client")
def _client():
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


def _db_path() -> str:
    # Always use a test-specific DB file to avoid interfering with other tests
    base = Path(__file__).resolve().parent.parent.parent / "data"
    base.mkdir(parents=True, exist_ok=True)
    # Reuse a single file per test run (set by env) or create one lazily
    env = os.getenv("DB_PATH")
    if not env:
        test_db = base / f"test_cashflow_{uuid.uuid4().hex[:8]}.db"
        os.environ["DB_PATH"] = str(test_db)
        return str(test_db)
    return env


def _seed_cashflow(project_id: str = "CF1", monto: float = 1000.0):
    # Ensure DB_PATH is established first
    path = _db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as con:
        cur = con.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS cashflow_planned(
              id INTEGER PRIMARY KEY,
              project_id TEXT,
              fecha TEXT,
              monto REAL,
              category TEXT
            );
            """
        )
        cur.execute(
            "DELETE FROM cashflow_planned WHERE project_id = ?",
            (project_id,),
        )
        cur.execute(
            "INSERT INTO cashflow_planned(project_id, fecha, monto, category) "
            "VALUES(?,?,?,?)",
            (project_id, "2025-09-01", monto, "ventas"),
        )
        con.commit()


def test_ar_map_cashflow_within_tolerance(client):
    # Force a fresh DB for this test
    os.environ.pop("DB_PATH", None)
    _seed_cashflow()
    # Amount 1005 vs planned 1000 => diff 5 <= tol (1000) => suggestion
    rv = client.post(
        "/api/ar-map/suggestions",
        json={
            "invoice": {
                "total_amount": 1005,
                "issue_date": "2025-09-10",
                "customer_name": "",  # avoid name heuristics
            }
        },
    )
    assert rv.status_code == 200
    items = rv.get_json()["items"]
    assert any(it["project_id"] == "CF1" for it in items)
    assert any(
        "ep:amount±2%" in (r or "")
        for it in items
        for r in ((it.get("reasons") or []) + [it.get("reason")])
    )


def test_ar_map_cashflow_outside_tolerance(client):
    os.environ.pop("DB_PATH", None)
    _seed_cashflow()
    # Amount 3005 vs 1000 diff 2005 > tol (1000) => no cashflow suggestion
    rv = client.post(
        "/api/ar-map/suggestions",
        json={
            "invoice": {
                "total_amount": 3005,
                "issue_date": "2025-09-10",
                "customer_name": "",
            }
        },
    )
    assert rv.status_code == 200
    items = rv.get_json()["items"]
    assert not any(it["project_id"] == "CF1" for it in items)
    # Ensure we didn't accidentally get the tolerance reason
    assert not any(
        "ep:amount±2%" in (r or "")
        for it in items
        for r in ((it.get("reasons") or []) + [it.get("reason")])
    )
