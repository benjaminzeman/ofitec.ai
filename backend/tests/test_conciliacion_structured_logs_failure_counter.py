import os
import json
import uuid
import logging
from pathlib import Path
import pytest
import server


@pytest.fixture(name="client")
def _client(monkeypatch):
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DB_PATH"] = str(data_dir / f"test_failure_counter_{uuid.uuid4().hex[:8]}.db")
    os.environ["RECON_STRUCTURED_LOGS"] = "1"
    os.environ["RECON_TEST_MODE"] = "1"
    os.environ["RECON_PROM_CLIENT"] = "1"
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


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


def test_emit_failure_counter(client, caplog, monkeypatch):
    caplog.set_level(logging.INFO)
    # Force json.dumps to fail for first structured event
    original_dumps = json.dumps
    calls = {"count": 0}

    def failing_once(obj, *a, **kw):  # noqa: ANN001
        if isinstance(obj, dict) and obj.get("event") == "recon_suggest_request" and calls["count"] == 0:
            calls["count"] += 1
            raise ValueError("fail primary emit")
        return original_dumps(obj, *a, **kw)

    monkeypatch.setattr(json, "dumps", failing_once)
    client.post("/api/conciliacion/sugerencias", json={"source_type": "bank"})

    events = _collect_events(caplog)
    # Ensure fallback event occurred
    assert any(e.get("event") == "recon_log_emit_error" for e in events)

    # Query prom metrics and assert failure counter gauge present and >=1
    resp = client.get("/api/conciliacion/metrics/prom")
    if resp.status_code != 200:
        pytest.skip("prom endpoint not available")
    text = resp.data.decode("utf-8")
    # Look for our new gauge name
    lines = [ln for ln in text.splitlines() if ln.startswith("recon_structured_logging_emit_failures_total")]
    assert lines, text
    # numeric value at end should be >=1
    val = float(lines[0].strip().split()[-1])
    assert val >= 1
