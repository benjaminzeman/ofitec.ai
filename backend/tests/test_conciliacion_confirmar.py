import os
import sqlite3
import tempfile
from backend.server import app


def _new_db():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    os.environ["DB_PATH"] = tmp.name
    con = sqlite3.connect(tmp.name)
    return con, tmp.name


def test_confirmar_creates_reconciliation_and_alias():
    con, path = _new_db()
    try:
        # No need to pre-create tables: endpoint creates them idempotently.
        client = app.test_client()
        payload = {
            "context": "bank",
            "confidence": 0.87,
            "metadata": {
                "user_id": "tester",
                "notes": "ok",
                "alias": "BANCO CHILE",
                "canonical": "BANCO DE CHILE",
            },
            "links": [
                {"bank_movement_id": 1, "sales_invoice_id": 2, "amount": 150.5}
            ],
        }
        r = client.post("/api/conciliacion/confirmar", json=payload)
        assert r.status_code == 200
        data = r.get_json()
        rid = data["reconciliation_id"]
        assert rid > 0
        # Validate DB side effects
        cur = con.cursor()
        # reconciliation row
        row = cur.execute(
            "SELECT context, confidence FROM recon_reconciliations WHERE id=?",
            (rid,),
        ).fetchone()
        assert row is not None
        assert row[0] == "bank"
        # links row
        lrow = cur.execute(
            (
                "SELECT bank_movement_id, sales_invoice_id, amount "
                "FROM recon_links WHERE reconciliation_id=?"
            ),
            (rid,),
        ).fetchone()
        assert lrow == (1, 2, 150.5)
        # alias upsert
        arow = cur.execute(
            "SELECT canonical FROM recon_aliases WHERE alias=?",
            ("BANCO CHILE",),
        ).fetchone()
        assert arow is not None and arow[0] == "BANCO DE CHILE"
    finally:
        con.close()
        os.remove(path)
