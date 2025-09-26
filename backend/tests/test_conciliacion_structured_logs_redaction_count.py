import os
import json
import uuid
import logging
from pathlib import Path
import pytest
import server


@pytest.fixture(name="client")
def _client():
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DB_PATH"] = str(data_dir / f"test_redact_count_{uuid.uuid4().hex[:8]}.db")
    os.environ["RECON_STRUCTURED_LOGS"] = "1"
    os.environ["RECON_TEST_MODE"] = "1"
    os.environ["RECON_STRUCTURED_REDACT"] = "movement_id,limit"  # ensure redaction
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c
    os.environ.pop("RECON_STRUCTURED_REDACT", None)


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


def test_redaction_count_present(client, caplog):
    caplog.set_level(logging.INFO)
    client.post("/api/conciliacion/sugerencias", json={"source_type": "bank", "movement_id": 5})
    evts = _collect_events(caplog)
    sugg = next(e for e in evts if e.get("event") == "recon_suggest_request")
    # Movement id and limit should be redacted
    assert "movement_id" not in sugg
    assert "limit" not in sugg
    # redaction_count > 0
    assert sugg.get("redaction_count", 0) >= 2
