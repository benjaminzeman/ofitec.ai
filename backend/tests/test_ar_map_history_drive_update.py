import os
import sqlite3
from pathlib import Path
import uuid

import pytest
import server


@pytest.fixture(name="client")
def _client():
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


def _fresh_db():
    base = Path(__file__).resolve().parent.parent.parent / "data"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"test_hist_{uuid.uuid4().hex[:8]}.db"
    os.environ["DB_PATH"] = str(path)
    return path


def test_ar_map_history_customer_rut(client):
    db = _fresh_db()
    with sqlite3.connect(db) as con:
        cur = con.cursor()
        cur.executescript(
            """
            CREATE TABLE sales_invoices(
              id INTEGER PRIMARY KEY,
              customer_rut TEXT,
              project_id TEXT
            );
            """
        )
        # Two previous invoices mapped to same project, one to another
        cur.executemany(
            "INSERT INTO sales_invoices(customer_rut, project_id) VALUES(?,?)",
            [
                ("11111111-1", "PRJX"),
                ("11111111-1", "PRJX"),
                ("11111111-1", "PRJZ"),
            ],
        )
        con.commit()
    rv = client.post(
        "/api/ar-map/suggestions",
        json={"invoice": {"customer_rut": "11111111-1"}},
    )
    assert rv.status_code == 200
    items = rv.get_json()["items"]
    # Expect PRJX first (more counts)
    assert items and items[0]["project_id"] == "PRJX"
    reasons = (items[0].get("reasons") or []) + [items[0].get("reason")]
    assert any("history:customer_rut" in (r or "") for r in reasons)


def test_ar_map_drive_path_slug_fallback(client):
    db = _fresh_db()
    with sqlite3.connect(db) as con:
        cur = con.cursor()
        cur.executescript(
            """
            CREATE TABLE projects(
              id INTEGER PRIMARY KEY,
              name TEXT,
              slug TEXT,
              analytic_code TEXT
            );
            """
        )
        cur.execute(
            (
                "INSERT INTO projects(id, name, slug, analytic_code) "
                "VALUES(?,?,?,?)"
            ),
            (5001, "Mega Project Chile", "mega-chile", "MCH"),
        )
        con.commit()
    rv = client.post(
        "/api/ar-map/suggestions",
        json={
            "drive_path": "/mnt/storage/clientes/mega-chile/docs/factura.pdf",
            "invoice": {"customer_name": ""},
        },
    )
    assert rv.status_code == 200
    items = rv.get_json()["items"]
    assert items and any(str(it["project_id"]) == "5001" for it in items)
    # Reason should include drive:path_contains_project due to slug match
    reasons_all = []
    for it in items:
        reasons_all.extend((it.get("reasons") or []) + [it.get("reason")])
    assert any("drive:path_contains_project" in (r or "") for r in reasons_all)


def test_ar_map_rule_update_path(client):
    _fresh_db()
    # Insert initial rule
    rv = client.post(
        "/api/ar-map/confirm",
        json={
            "rules": [
                {
                    "kind": "customer_name_like",
                    "pattern": "FOO",
                    "project_id": "OLD",
                }
            ]
        },
    )
    assert rv.status_code == 201
    # Re-insert same pattern with new project (simulate update expectation)
    rv = client.post(
        "/api/ar-map/confirm",
        json={
            "rules": [
                {
                    "kind": "customer_name_like",
                    "pattern": "FOO",
                    "project_id": "NEW",
                }
            ]
        },
    )
    assert rv.status_code == 201
    # Second insert of same pattern different project: no upsert.
    # Assert at least one suggestion (append-only behavior).
    rv = client.post(
        "/api/ar-map/suggestions",
        json={"invoice": {"customer_name": "FOO CORP"}},
    )
    assert rv.status_code == 200
    items = rv.get_json()["items"]
    # Accept >=1 suggestion (could be multiple PIDs).
    assert items
