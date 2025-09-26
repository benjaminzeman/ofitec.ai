import os
import uuid
from pathlib import Path
import server
from db_utils import db_conn


def _isolated_db():
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DB_PATH"] = str(
        data_dir / f"test_amt_{uuid.uuid4().hex[:8]}.db"
    )


def test_negative_amount_normalized_to_zero():
    _isolated_db()
    client = server.app.test_client()
    payload = {
        "context": "bank",
        "links": [
            {"bank_movement_id": 1, "amount": -50},
            {"sales_invoice_id": 2, "amount": -50},
        ],
    }
    r = client.post("/api/conciliacion/confirmar", json=payload)
    assert r.status_code == 200

    with db_conn() as con:
        cur = con.cursor()
        cur.execute("SELECT amount FROM recon_links ORDER BY id ASC")
        amounts = [row[0] for row in cur.fetchall()]
        # All negative amounts should have been coerced to 0.0
        assert all(a == 0 for a in amounts)
