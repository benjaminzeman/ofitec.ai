import os
import uuid
from pathlib import Path
import pytest
from backend import server


@pytest.fixture(name="client")
def _client():
    # Isolate DB per module run to avoid cross-schema conflicts
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DB_PATH"] = str(
        data_dir / f"test_conc_{uuid.uuid4().hex[:8]}.db"
    )
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c

# --- /api/conciliacion/sugerencias ---


def test_conciliacion_sugerencias_invalid_context(client):
    r = client.post(
        "/api/conciliacion/sugerencias", json={"source_type": "foo"}
    )
    assert r.status_code == 422
    data = r.get_json()
    assert data["error"] == "invalid_context"


def test_conciliacion_sugerencias_valid_empty(client):
    r = client.post(
        "/api/conciliacion/sugerencias", json={"source_type": "bank"}
    )
    assert r.status_code == 200
    assert r.get_json()["items"] == []  # adapter fallback returns []

# --- /api/conciliacion/preview ---


def test_conciliacion_preview_requires_links(client):
    r = client.post("/api/conciliacion/preview", json={})
    assert r.status_code == 422
    assert r.get_json()["error"] == "invalid_payload"


def test_conciliacion_preview_accumulates(client):
    r = client.post(
        "/api/conciliacion/preview",
        json={
            "links": [
                {"sales_invoice_id": 1, "amount": 100},
                {"sales_invoice_id": 1, "amount": 50},
                {"bank_movement_id": 10, "amount": 25},
                {"bank_movement_id": 10, "amount": 25},
            ]
        },
    )
    assert r.status_code == 200
    data = r.get_json()["preview"]
    assert data["invoice_deltas"]["sales:1"] == 150
    assert data["movement_deltas"]["10"] == 50

# --- /api/conciliacion/confirmar ---


def test_conciliacion_confirmar_simple_intention(client):
    r = client.post(
        "/api/conciliacion/confirmar",
        json={
            "source_ref": "bm#1",
            "target_ref": "sales#1",
            "context": "bank",
            "metadata": {"user_id": "u1", "notes": "ok"},
        },
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["accepted"] is True


def test_conciliacion_confirmar_with_links_and_alias(client):
    r = client.post(
        "/api/conciliacion/confirmar",
        json={
            "context": "sales",
            "links": [
                {"bank_movement_id": 11, "amount": 120.5},
                {"sales_invoice_id": 2, "amount": 120.5},
            ],
            "metadata": {
                "user_id": "u2",
                "notes": "match",
                "alias": "ACME",
                "canonical": "ACME S.A.",
            },
            "confidence": 0.87,
        },
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    # fetch historial should list at least one item
    h = client.get("/api/conciliacion/historial")
    assert h.status_code == 200
    items = h.get_json()["items"]
    assert any(it["context"] in ("bank", "sales") for it in items)

# --- /api/conciliacion/links ---


def test_conciliacion_links_empty_params_returns_empty(client):
    r = client.get("/api/conciliacion/links")
    assert r.status_code == 200
    assert r.get_json()["items"] == []


def test_conciliacion_links_bank_anchor(client):
    # Create reconciliation with bank+sales link so we can query by bank id
    client.post(
        "/api/conciliacion/confirmar",
        json={
            "context": "bank",
            "links": [
                {"bank_movement_id": 210, "amount": 300},
                {"sales_invoice_id": 5, "amount": 300},
            ],
        },
    )
    r = client.get("/api/conciliacion/links?bank_id=210")
    assert r.status_code == 200
    items = r.get_json()["items"]
    # Should return at least one linked item
    assert len(items) >= 1
