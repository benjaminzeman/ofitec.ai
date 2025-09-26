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
    os.environ["DB_PATH"] = str(data_dir / f"test_structlog_{uuid.uuid4().hex[:8]}.db")
    os.environ["RECON_STRUCTURED_LOGS"] = "1"
    os.environ["RECON_TEST_MODE"] = "1"
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


def test_structured_log_emitted_on_suggest(client, caplog):
    caplog.set_level(logging.INFO)
    r = client.post("/api/conciliacion/sugerencias", json={"source_type": "bank"})
    assert r.status_code == 200
    # Find structured line
    found = None
    for rec in caplog.records:
        msg = rec.getMessage()
        if '"event": "recon_suggest_request"' in msg:
            found = msg
            break
    assert found is not None, "Expected structured recon_suggest_request log line"
    data = json.loads(found)
    # Basic required keys
    for key in [
        "event",
        "outcome",
        "latency_seconds",
        "latency_window",
        "slo_p95_target",
        "slo_violations_total",
        "window_size",
        "sample_count",
    ]:
        assert key in data
    assert data["event"] == "recon_suggest_request"
    # latency_window has quantiles
    for qk in ["p50", "p95", "p99", "avg"]:
        assert qk in data["latency_window"]
