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
    os.environ["DB_PATH"] = str(data_dir / f"test_fallback_{uuid.uuid4().hex[:8]}.db")
    os.environ["RECON_STRUCTURED_LOGS"] = "1"
    os.environ["RECON_TEST_MODE"] = "1"
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


def test_fallback_emission(client, caplog, monkeypatch):
    caplog.set_level(logging.INFO)
    # Force json.dumps to fail exactly once for the primary event
    original_dumps = json.dumps
    calls = {"count": 0}

    def failing_dumps(obj, *a, **kw):  # noqa: ANN001
        if isinstance(obj, dict) and obj.get("event") == "recon_suggest_request" and calls["count"] == 0:
            calls["count"] += 1
            raise ValueError("boom serialize")
        return original_dumps(obj, *a, **kw)

    monkeypatch.setattr(json, "dumps", failing_dumps)
    client.post("/api/conciliacion/sugerencias", json={"source_type": "bank"})
    events = _collect_events(caplog)
    # Expect fallback error event present
    assert any(e.get("event") == "recon_log_emit_error" for e in events), events
    err_ev = next(e for e in events if e.get("event") == "recon_log_emit_error")
    assert err_ev["original_event"] == "recon_suggest_request"
    assert err_ev["exception_class"] == "ValueError"
    assert "schema_version" in err_ev
