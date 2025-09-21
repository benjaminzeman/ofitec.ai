import os
import uuid
from pathlib import Path
from backend import server
from backend.db_utils import db_conn


def _isolated_db():
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DB_PATH"] = str(
        data_dir / f"test_alias_{uuid.uuid4().hex[:8]}.db"
    )


def test_alias_truncation_and_upsert():
    _isolated_db()
    client = server.app.test_client()
    long_alias = "A" * 300
    long_canonical = "B" * 300
    payload = {
        "context": "bank",
        "links": [
            {"bank_movement_id": 1, "amount": 10},
            {"sales_invoice_id": 2, "amount": 10},
        ],
        "metadata": {
            "user_id": "tester",
            "alias": long_alias,
            "canonical": long_canonical,
        },
    }
    r = client.post("/api/conciliacion/confirmar", json=payload)
    assert r.status_code == 200

    with db_conn() as con:
        cur = con.cursor()
        cur.execute("SELECT alias, canonical FROM recon_aliases")
        row = cur.fetchone()
        assert row is not None
        assert len(row[0]) == 120
        assert len(row[1]) == 120

    # Second post with different canonical for same alias -> should update
    payload["metadata"]["canonical"] = "NEW_CANON"
    r2 = client.post("/api/conciliacion/confirmar", json=payload)
    assert r2.status_code == 200
    with db_conn() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT canonical FROM recon_aliases WHERE alias=?",
            (row[0],),
        )
        updated = cur.fetchone()[0]
        assert updated == "NEW_CANON"
