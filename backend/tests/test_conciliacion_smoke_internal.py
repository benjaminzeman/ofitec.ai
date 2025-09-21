import os
import uuid
from pathlib import Path
from backend import server
from backend.db_utils import db_conn

def _isolated_db():
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DB_PATH"] = str(data_dir / f"test_smoke_{uuid.uuid4().hex[:6]}.db")


def test_smoke_combined_and_negative_normalization():
    _isolated_db()
    client = server.app.test_client()
    payload = {
        "context": "bank",
        "links": [
            {"bank_movement_id": 900, "amount": -40},
            {"sales_invoice_id": 901, "amount": 40},
        ],
        "metadata": {"alias": "BANK XYZ", "canonical": "BANK XYZ SPA"},
    }
    r = client.post("/api/conciliacion/confirmar", json=payload)
    assert r.status_code == 200
    rid = r.get_json()["reconciliation_id"]
    assert rid > 0
    # recon_links should contain at least one row with amount 0 normalized OR combined row >0 plus individual normalization logic
    with db_conn() as con:
        cur = con.cursor()
        cur.execute("SELECT bank_movement_id, sales_invoice_id, amount FROM recon_links")
        rows = cur.fetchall()
        assert rows, "No links inserted"
        # At least one row must reference both sides (combined) or two rows referencing each side separately
        has_bank_sales = any(r[0] is not None and r[1] is not None for r in rows)
        assert has_bank_sales, f"Missing combined row: {rows}"
        # Negative was normalized
        assert all(a is None or a >= 0 for (_, _, a) in rows)


def test_smoke_invalid_payload_code():
    _isolated_db()
    client = server.app.test_client()
    r = client.post("/api/conciliacion/confirmar", json={"context": "bank"})
    assert r.status_code == 422
    assert r.get_json()["error"] == "invalid_payload"
