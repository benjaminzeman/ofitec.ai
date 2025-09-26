import os
import uuid
import logging
import random
from pathlib import Path
import pytest
import server


@pytest.fixture(name="client")
def _client():
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DB_PATH"] = str(data_dir / f"test_per_event_sampling_{uuid.uuid4().hex[:8]}.db")
    os.environ["RECON_STRUCTURED_LOGS"] = "1"
    os.environ["RECON_TEST_MODE"] = "1"
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


def _count_events(caplog, name: str):
    cnt = 0
    for rec in caplog.records:
        msg = rec.getMessage()
        if f'"event": "{name}"' in msg:
            cnt += 1
    return cnt


def test_per_event_sampling_overrides(client, caplog):
    caplog.set_level(logging.INFO)
    # Global mid-rate
    os.environ["RECON_STRUCTURED_LOG_SAMPLE"] = "0.5"
    # Force suggest events to always emit, confirmar to never emit
    os.environ["RECON_STRUCTURED_LOG_SAMPLE_RECON_SUGGEST_REQUEST"] = "1.0"
    os.environ["RECON_STRUCTURED_LOG_SAMPLE_RECON_CONFIRMAR_REQUEST"] = "0.0"
    random.seed(777)

    N = 60
    for i in range(N):
        client.post("/api/conciliacion/sugerencias", json={"source_type": "bank", "movement_id": i})
        client.post("/api/conciliacion/confirmar", json={"movement_id": i})

    sug = _count_events(caplog, "recon_suggest_request")
    conf = _count_events(caplog, "recon_confirmar_request")

    # Suggest should have emitted ~all (allowing for fallback emission anomalies)
    assert sug >= N * 0.95, f"expected nearly all suggest events emitted, got {sug}/{N}"
    # Confirmar should have emitted zero (or near zero if a non-deterministic path)
    assert conf == 0, f"expected confirmar overridden to 0 sample rate, got {conf}"

    # Clean up env
    for k in [
        "RECON_STRUCTURED_LOG_SAMPLE",
        "RECON_STRUCTURED_LOG_SAMPLE_RECON_SUGGEST_REQUEST",
        "RECON_STRUCTURED_LOG_SAMPLE_RECON_CONFIRMAR_REQUEST",
    ]:
        os.environ.pop(k, None)
