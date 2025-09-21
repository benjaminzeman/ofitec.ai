import os
import json
import uuid
from pathlib import Path
import logging
import pytest
from backend import server


@pytest.fixture(name="client")
def _client():
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DB_PATH"] = str(data_dir / f"test_reqid_{uuid.uuid4().hex[:8]}.db")
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


def test_request_id_propagates_suggest(client, caplog):
    caplog.set_level(logging.INFO)
    rid = "RID-ABC-123"
    client.post("/api/conciliacion/sugerencias", json={"source_type": "bank"}, headers={"X-Request-Id": rid})
    evt = _find_event(caplog, "recon_suggest_request")
    assert evt is not None
    assert evt["request_id"] == rid


def test_request_id_propagates_confirmar(client, caplog):
    caplog.set_level(logging.INFO)
    rid = "RID-CNF-456"
    client.post(
        "/api/conciliacion/confirmar",
        json={
            "movement_id": 77,
            "metadata": {"note": "ok"},
        },
        headers={"X-Request-Id": rid},
    )
    evt = _find_event(caplog, "recon_confirmar_request")
    assert evt is not None
    assert evt["request_id"] == rid
