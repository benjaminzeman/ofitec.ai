import os
import json
import uuid
from pathlib import Path
import logging
import pytest
import server


@pytest.fixture(name="client")
def _client():
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DB_PATH"] = str(data_dir / f"test_conf_struct_{uuid.uuid4().hex[:8]}.db")
    os.environ["RECON_STRUCTURED_LOGS"] = "1"
    os.environ["RECON_TEST_MODE"] = "1"
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


def _find_event(caplog, name: str):
    for rec in caplog.records:
        msg = rec.getMessage()
        if f'"event": "{name}"' in msg:
            return json.loads(msg)
    return None


def test_confirmar_simple_intention_log(client, caplog):
    caplog.set_level(logging.INFO)
    r = client.post(
        "/api/conciliacion/confirmar",
        json={
            "source_ref": "bm#1",
            "target_ref": "sales#1",
            "context": "bank",
            "metadata": {"user_id": "u1"},
        },
    )
    assert r.status_code == 200
    evt = _find_event(caplog, "recon_confirmar_request")
    assert evt is not None
    assert evt["variant"] == "simple_intention"
    assert evt["accepted"] is True


def test_confirmar_movement_only_log(client, caplog):
    caplog.set_level(logging.INFO)
    r = client.post(
        "/api/conciliacion/confirmar",
        json={
            "movement_id": 123,
            "metadata": {"user_id": "u2"},
        },
    )
    assert r.status_code == 200
    evt = _find_event(caplog, "recon_confirmar_request")
    assert evt is not None
    assert evt["variant"] == "movement_only"
    assert evt["movement_id"] == 123


def test_confirmar_legacy_links_log(client, caplog):
    caplog.set_level(logging.INFO)
    r = client.post(
        "/api/conciliacion/confirmar",
        json={
            "context": "sales",
            "links": [
                {"bank_movement_id": 200, "amount": 10},
                {"sales_invoice_id": 50, "amount": 10},
            ],
            "metadata": {"alias": "FOO", "canonical": "FOO SA"},
        },
    )
    assert r.status_code == 200
    evt = _find_event(caplog, "recon_confirmar_request")
    assert evt is not None
    assert evt["variant"] == "legacy_links"
    assert evt["links_count"] == 2
    assert evt["alias_present"] is True
