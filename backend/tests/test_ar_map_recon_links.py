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


def _fresh_db():
    # Isolate DB per test to avoid crosstalk
    base = Path(__file__).resolve().parent.parent.parent / "data"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"test_recon_{uuid.uuid4().hex[:8]}.db"
    os.environ["DB_PATH"] = str(path)
    return path


def _seed_recon_ap():
    db = _fresh_db()
    with sqlite3.connect(db) as con:
        cur = con.cursor()
        cur.executescript(
            """
            CREATE TABLE recon_links(
              id INTEGER PRIMARY KEY,
              reconciliation_id INTEGER,
              sales_invoice_id INTEGER,
              purchase_invoice_id INTEGER,
              expense_id INTEGER
            );
            CREATE TABLE ap_invoices(
              id INTEGER PRIMARY KEY,
              project_name TEXT
            );
            CREATE TABLE projects_analytic_map(
              id INTEGER PRIMARY KEY,
              zoho_project_id TEXT,
              zoho_project_name TEXT
            );
            """
        )
        # Project mapping
        cur.execute(
            (
                "INSERT INTO projects_analytic_map(zoho_project_id, "
                "zoho_project_name) VALUES(?,?)"
            ),
            ("PX1", "Proyecto X"),
        )
        # AP invoice referencing project name
        cur.execute(
            "INSERT INTO ap_invoices(id, project_name) VALUES(?,?)",
            (2001, "Proyecto X"),
        )
        # Link with sales invoice 1001
        cur.execute(
            (
                "INSERT INTO recon_links(reconciliation_id, sales_invoice_id, "
                "purchase_invoice_id) VALUES(?,?,?)"
            ),
            (9001, 1001, 2001),
        )
        con.commit()
    return 1001


def _seed_recon_expense():
    db = _fresh_db()
    with sqlite3.connect(db) as con:
        cur = con.cursor()
        cur.executescript(
            """
            CREATE TABLE recon_links(
              id INTEGER PRIMARY KEY,
              reconciliation_id INTEGER,
              sales_invoice_id INTEGER,
              purchase_invoice_id INTEGER,
              expense_id INTEGER
            );
            CREATE TABLE expenses(
              id INTEGER PRIMARY KEY,
              proyecto TEXT
            );
            CREATE TABLE projects_analytic_map(
              id INTEGER PRIMARY KEY,
              zoho_project_id TEXT,
              zoho_project_name TEXT
            );
            """
        )
        cur.execute(
            (
                "INSERT INTO projects_analytic_map(zoho_project_id, "
                "zoho_project_name) VALUES(?,?)"
            ),
            ("PZ9", "Zeta Proj"),
        )
        cur.execute(
            "INSERT INTO expenses(id, proyecto) VALUES(?,?)",
            (3002, "Zeta Proj"),
        )
        cur.execute(
            (
                "INSERT INTO recon_links(reconciliation_id, sales_invoice_id, "
                "expense_id) VALUES(?,?,?)"
            ),
            (9100, 1102, 3002),
        )
        con.commit()
    return 1102


def test_ar_map_recon_link_ap_invoice(client):
    sales_id = _seed_recon_ap()
    rv = client.post(
        "/api/ar-map/suggestions",
        json={"invoice": {"invoice_id": sales_id}},
    )
    assert rv.status_code == 200
    items = rv.get_json()["items"]
    reasons = []
    for it in items:
        reasons.extend((it.get("reasons") or []) + [it.get("reason")])
    assert any("recon:co-linked ap" in (r or "") for r in reasons)


def test_ar_map_recon_link_expense(client):
    sales_id = _seed_recon_expense()
    rv = client.post(
        "/api/ar-map/suggestions",
        json={"invoice": {"invoice_id": sales_id}},
    )
    assert rv.status_code == 200
    items = rv.get_json()["items"]
    reasons = []
    for it in items:
        reasons.extend((it.get("reasons") or []) + [it.get("reason")])
    assert any("recon:co-linked expense" in (r or "") for r in reasons)
