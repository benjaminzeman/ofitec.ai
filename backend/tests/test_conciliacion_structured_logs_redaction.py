import os
import json
import uuid
import logging
from pathlib import Path
import pytest
from backend import server


@pytest.fixture(name="client")
def _client():
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DB_PATH"] = str(data_dir / f"test_redact_{uuid.uuid4().hex[:8]}.db")
    os.environ["RECON_STRUCTURED_LOGS"] = "1"
    os.environ["RECON_TEST_MODE"] = "1"
    os.environ["RECON_DEBUG_FLAGS"] = "dbgA,dbgB"  # ensure flags appear
    os.environ["RECON_STRUCTURED_REDACT"] = "movement_id,limit,debug_flags"  # redact non-core and also debug_flags
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c
    # cleanup env leakage
    for k in ["RECON_STRUCTURED_REDACT", "RECON_DEBUG_FLAGS"]:
        os.environ.pop(k, None)


def _collect_events(caplog):
    out = []
    for rec in caplog.records:
        msg = rec.getMessage()
        if msg.startswith("{") and '"event"' in msg:
            try:
                out.append(json.loads(msg))
            except Exception:  # pragma: no cover
                pass
    return out


def test_redaction_and_debug_flags(client, caplog):
    caplog.set_level(logging.INFO)
    client.post("/api/conciliacion/sugerencias", json={"source_type": "bank", "movement_id": 11})
    events = _collect_events(caplog)
    assert events
    # find suggest event
    sugg = None
    for e in events:
        if e.get("event") == "recon_suggest_request":
            sugg = e
            break
    assert sugg, "suggest event not found"
    # Core fields must remain
    for core in ["event", "request_id", "timestamp", "schema_version"]:
        assert core in sugg
    # Redacted fields should be absent
    assert "movement_id" not in sugg
    assert "limit" not in sugg
    # debug_flags was redacted
    assert "debug_flags" not in sugg


def test_schema_endpoint_lists_redacted_and_debug_env(client):
    # Ensure schema endpoint accessible
    resp = client.get("/api/conciliacion/logs/schema")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["schema_version"] >= 1
    assert "events" in data and isinstance(data["events"], dict)
    assert data["redaction_env"] == "RECON_STRUCTURED_REDACT"
    assert data["debug_flags_env"] == "RECON_DEBUG_FLAGS"
