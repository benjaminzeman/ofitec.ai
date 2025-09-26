import os
import uuid
from pathlib import Path
import pytest
import server


@pytest.fixture(name="client")
def _client():
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DB_PATH"] = str(data_dir / f"test_prom_{uuid.uuid4().hex[:8]}.db")
    os.environ["RECON_STRUCTURED_LOGS"] = "1"
    os.environ["RECON_PROM_CLIENT"] = "1"
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


def test_prom_exposes_structured_logging_metrics(client):
    # generate a couple of events
    client.post("/api/conciliacion/sugerencias", json={"source_type": "bank", "movement_id": 1})
    client.post("/api/conciliacion/confirmar", json={"movement_id": 2})
    resp = client.get("/api/conciliacion/metrics/prom")
    if resp.status_code == 404:  # prometheus client missing in env; skip
        pytest.skip("prometheus client not enabled")
    body = resp.data.decode("utf-8")
    # Core structured logging gauges
    assert "recon_structured_logging_enabled" in body
    assert "recon_structured_logging_emitted_total" in body
    assert "recon_structured_logging_sampled_out_total" in body
    assert "recon_structured_logging_schema_version" in body
