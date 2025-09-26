import os
import uuid
import logging
from pathlib import Path
import pytest
import server


@pytest.fixture(name="client")
def _client():
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DB_PATH"] = str(data_dir / f"test_logs_config_{uuid.uuid4().hex[:8]}.db")
    os.environ["RECON_STRUCTURED_LOGS"] = "1"
    os.environ["RECON_TEST_MODE"] = "1"
    os.environ["RECON_STRUCTURED_LOG_SAMPLE"] = "0.33"
    os.environ["RECON_STRUCTURED_LOG_SAMPLE_RECON_SUGGEST_REQUEST"] = "0.9"
    os.environ["RECON_STRUCTURED_LOG_SAMPLE_RECON_CONFIRMAR_REQUEST"] = "0.1"
    os.environ["RECON_STRUCTURED_REDACT"] = "secret_field,another"
    os.environ["RECON_DEBUG_FLAGS"] = "alpha,beta"
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


def test_config_endpoint_shape(client, caplog):
    caplog.set_level(logging.INFO)
    resp = client.get("/api/conciliacion/logs/config")
    assert resp.status_code == 200, resp.data
    body = resp.get_json()
    assert body["enabled"] is True
    assert 0 <= body["global_sample_rate"] <= 1
    overrides = body["per_event_sample_overrides"]
    assert overrides.get("RECON_SUGGEST_REQUEST") == 0.9
    assert overrides.get("RECON_CONFIRMAR_REQUEST") == 0.1
    assert sorted(body["redacted_fields"]) == ["another", "secret_field"]
    assert body["debug_flags"] == ["alpha", "beta"]
    counters = body["counters"]
    assert {"emitted_total", "sampled_out_total", "emit_failures_total"}.issubset(counters.keys())
    env_keys = body["env_keys"]
    assert env_keys["global_sample"] == "RECON_STRUCTURED_LOG_SAMPLE"
    assert env_keys["per_event_prefix"] == "RECON_STRUCTURED_LOG_SAMPLE_"
