import os
import json
import uuid
import logging
from pathlib import Path
import re
import pytest
from backend import server


@pytest.fixture(name="client")
def _client():
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DB_PATH"] = str(data_dir / f"test_schema_{uuid.uuid4().hex[:8]}.db")
    os.environ["RECON_STRUCTURED_LOGS"] = "1"
    os.environ["RECON_TEST_MODE"] = "1"
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


CORE_KEYS = {"event", "request_id", "timestamp", "schema_version"}

SUGGEST_KEYS = CORE_KEYS | {"outcome", "latency_seconds", "latency_window", "sample_count"}
CONFIRMAR_KEYS = CORE_KEYS | {"variant", "accepted"}
METRICS_RESET_KEYS = CORE_KEYS | {"before", "after"}

_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def _collect_events(caplog):
    events = []
    for rec in caplog.records:
        msg = rec.getMessage()
        if msg.startswith("{") and '"event"' in msg:
            try:
                events.append(json.loads(msg))
            except Exception:  # pragma: no cover
                pass
    return events


def test_schema_core_and_specific_fields(client, caplog):
    caplog.set_level(logging.INFO)
    client.post("/api/conciliacion/sugerencias", json={"source_type": "bank"})
    client.post(
        "/api/conciliacion/confirmar",
        json={
            "source_ref": "bm#1",
            "target_ref": "sales#1",
            "context": "bank",
            "metadata": {"user_id": "u1"},
        },
    )
    os.environ.pop("RECON_DISABLE_METRICS", None)
    os.environ.pop("RECON_METRICS_DISABLED", None)
    os.environ["RECON_METRICS_RESET_TOKEN"] = "tkn"
    client.post("/api/conciliacion/metrics/reset", json={"token": "tkn"})

    events = _collect_events(caplog)
    assert events, "No structured events captured"

    for evt in events:
        missing = CORE_KEYS - set(evt)
        assert not missing, f"Missing core keys: {missing} in {evt.get('event')}"
        assert isinstance(evt["request_id"], str) and evt["request_id"], "request_id must be a non-empty string"
        assert isinstance(evt["schema_version"], int) and evt["schema_version"] >= 1
        assert _TS_RE.match(evt["timestamp"]), f"Invalid timestamp format: {evt['timestamp']}"

    types = {e["event"] for e in events}
    assert "recon_suggest_request" in types
    assert "recon_confirmar_request" in types

    for e in events:
        if e["event"] == "recon_suggest_request":
            assert SUGGEST_KEYS <= e.keys()
        elif e["event"] == "recon_confirmar_request":
            assert CONFIRMAR_KEYS <= e.keys()
        elif e["event"] == "recon_metrics_reset":
            assert METRICS_RESET_KEYS <= e.keys()
