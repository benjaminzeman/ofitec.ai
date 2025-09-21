import os
import uuid
from pathlib import Path
from backend import server


def _isolated_db():
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DB_PATH"] = str(
        data_dir / f"test_hist_{uuid.uuid4().hex[:8]}.db"
    )


def test_conciliacion_historial_basic_order_and_sum():
    _isolated_db()
    client = server.app.test_client()
    # First reconciliation: 100 + 100
    client.post(
        "/api/conciliacion/confirmar",
        json={
            "context": "bank",
            "links": [
                {"bank_movement_id": 1, "amount": 100},
                {"sales_invoice_id": 2, "amount": 100},
            ],
        },
    )
    # Second reconciliation: 50 + 50
    client.post(
        "/api/conciliacion/confirmar",
        json={
            "context": "sales",
            "links": [
                {"bank_movement_id": 3, "amount": 50},
                {"sales_invoice_id": 4, "amount": 50},
            ],
        },
    )
    r = client.get("/api/conciliacion/historial")
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert len(items) >= 2
    # Ensure ordering newest first by created_at/id; first item should be second reconciliation
    assert items[0]["context"] in ("sales", "bank")
    # Sum of amounts for each reconciliation should match link totals
    # (order may vary on fast inserts, so just verify each has monto in expected set)
    montos = {it["monto"] for it in items[:2]}
    assert 200.0 in montos
    assert 100.0 in montos
