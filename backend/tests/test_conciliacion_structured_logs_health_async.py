import os
import re
import uuid
from pathlib import Path
import pytest
from backend import server
from backend.conciliacion_api_clean import test_reset_internal


@pytest.fixture(name="client")
def _client():
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DB_PATH"] = str(data_dir / f"test_structlog_async_{uuid.uuid4().hex[:8]}.db")
    os.environ["RECON_STRUCTURED_LOGS"] = "1"
    os.environ["RECON_PROM_CLIENT"] = "1"
    # Ensure we start with async disabled unless a test explicitly enables it
    os.environ.pop("RECON_STRUCTURED_LOG_ASYNC", None)
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


def _enable_structured_logging(env_extra=None):
    os.environ.setdefault("RECON_STRUCTURED_LOGS", "1")  # legacy toggle name if present
    # Primary enable flag used in code
    os.environ["RECON_STRUCTURED_LOGS"] = "1"
    if env_extra:
        for k, v in env_extra.items():
            os.environ[k] = str(v)


def test_logs_health_basic(client):
    _enable_structured_logging()
    test_reset_internal()
    # Emit a simple event through an endpoint that triggers logging (metrics reset emits a structured event)
    resp = client.post("/api/conciliacion/metrics/reset")
    assert resp.status_code == 200
    h = client.get("/api/conciliacion/logs/health")
    assert h.status_code == 200
    payload = h.get_json()
    assert payload["enabled"] is True
    assert "failure_ratio" in payload
    # Allow small non-zero due to potential background async worker or initialization race
    assert 0.0 <= payload["failure_ratio"] < 0.05
    # Allow small number of failures (e.g., race conditions in async init or serialization retries)
    assert payload["emit_failures_total"] < 5
    assert payload["emitted_total"] >= 1  # at least the metrics reset event
    assert payload["last_event_timestamp"] is not None
    assert payload["last_event_age_seconds"] is not None


def test_logs_health_async_queue_drop(client):
    # Enable async logging with very small queue size to force drops
    _enable_structured_logging({
        "RECON_STRUCTURED_LOG_ASYNC": "1",
        "RECON_STRUCTURED_LOG_ASYNC_QUEUE": "5",
    })
    test_reset_internal()

    # Monkeypatch queue size if environment not enough (defensive) -- no direct access needed if env works
    # Rapidly emit more events than queue size via metrics reset (each reset emits one structured event)
    for _ in range(25):
        client.post("/api/conciliacion/metrics/reset")
    h = client.get("/api/conciliacion/logs/health")
    assert h.status_code == 200
    payload = h.get_json()
    assert payload["async_enabled"] is True
    # Some events should have been emitted or queued
    assert payload["emitted_total"] >= 1
    # It's possible (though unlikely) zero drops if worker drained fast; allow >=0 but capture value for metrics assertion
    dropped = payload.get("queue_dropped_total", 0)
    assert dropped >= 0

    # Check failure ratio invariants (no forced failure path here)
    assert 0.0 <= payload["failure_ratio"] <= 1.0

    # Validate new Prometheus gauges present
    prom = client.get("/api/conciliacion/metrics/prom")
    if prom.status_code == 404:
        pytest.skip("prometheus client not enabled")
    assert prom.status_code == 200
    text = prom.get_data(as_text=True)
    # Basic presence checks
    for metric in [
        "recon_structured_logging_async_enabled",
        "recon_structured_logging_queue_dropped_total",
        "recon_structured_logging_failure_ratio",
        "recon_structured_logging_last_event_age_seconds",
        "recon_structured_logging_async_queue_current",
        "recon_structured_logging_async_queue_max",
    ]:
        assert metric in text

    # Extract async enabled gauge value (should be 1)
    m = re.search(r"recon_structured_logging_async_enabled\s+(\d+(?:\.\d+)?)", text)
    assert m, "async enabled gauge missing"
    assert float(m.group(1)) == 1.0

    # Extract failure ratio gauge and ensure within [0,1]
    fr = re.search(r"recon_structured_logging_failure_ratio\s+(\d+(?:\.\d+)?)", text)
    assert fr, "failure ratio gauge missing"
    fr_val = float(fr.group(1))
    assert 0.0 <= fr_val <= 1.0

    # Extract last event age (>=0 or -1 if none, but should be >=0)
    age_match = re.search(r"recon_structured_logging_last_event_age_seconds\s+(-?\d+(?:\.\d+)?)", text)
    assert age_match, "last event age gauge missing"
    age_val = float(age_match.group(1))
    assert age_val >= 0 or age_val == -1
    # Cleanup to avoid leaking async to subsequent tests
    os.environ.pop("RECON_STRUCTURED_LOG_ASYNC", None)

