import time

from flask import Flask
from conciliacion_api_clean import bp as conciliacion_bp  # type: ignore


def make_app():
    app = Flask(__name__)
    app.register_blueprint(conciliacion_bp)
    return app


def test_runtime_override_global_sample_rate(monkeypatch):
    monkeypatch.setenv("RECON_TEST_MODE", "1")  # enable structured logs
    app = make_app()
    client = app.test_client()

    # Baseline: no overrides
    r0 = client.get("/api/conciliacion/logs/config")
    assert r0.status_code == 200
    r0j = r0.get_json()
    base_sample = r0j["global_sample_rate"]
    assert base_sample == 1.0  # default when unset

    # Apply runtime override to reduce global sample rate
    r1 = client.post("/api/conciliacion/logs/runtime", json={"global_sample_rate": 0.0})
    assert r1.status_code == 200, r1.data
    r1j = r1.get_json()
    assert r1j["effective_overrides"]["global_sample_rate"] == 0.0

    # Fire some suggest events that would normally emit; with sample 0 no additional events should emit.
    h_before = client.get("/api/conciliacion/logs/health").get_json()
    emitted_before = h_before["emitted_total"]
    sampled_out_before = h_before["sampled_out_total"]
    for i in range(5):
        client.post("/api/conciliacion/suggest", json={"movement_id": i+1, "limit": 1})

    r2 = client.get("/api/conciliacion/logs/health")
    assert r2.status_code == 200
    r2j = r2.get_json()
    # Emitted total should not have increased
    assert r2j["emitted_total"] == emitted_before
    # Sampled out should reflect the skipped events (at least number fired)
    assert r2j["sampled_out_total"] >= sampled_out_before + 1

    # Raise sampling to 1.0 via override and ensure events now emit
    r3 = client.post("/api/conciliacion/logs/runtime", json={"global_sample_rate": 1.0})
    assert r3.status_code == 200
    for i in range(3):
        client.post("/api/conciliacion/suggest", json={"movement_id": 100+i, "limit": 1})
    r4 = client.get("/api/conciliacion/logs/health")
    r4j = r4.get_json()
    assert r4j["emitted_total"] >= 1


def test_runtime_override_async_toggle(monkeypatch):
    monkeypatch.setenv("RECON_TEST_MODE", "1")
    app = make_app()
    client = app.test_client()

    # Ensure async disabled baseline
    h0 = client.get("/api/conciliacion/logs/health")
    assert h0.status_code == 200
    h0j = h0.get_json()
    assert h0j["async_enabled"] is False

    # Enable async via override
    r1 = client.post("/api/conciliacion/logs/runtime", json={"async_enabled": True})
    assert r1.status_code == 200
    h1 = client.get("/api/conciliacion/logs/health")
    h1j = h1.get_json()
    assert h1j["async_enabled"] is True

    # Trigger events to populate queue metrics
    for i in range(5):
        client.post("/api/conciliacion/suggest", json={"movement_id": i+200, "limit": 1})
    # Allow background thread to drain
    time.sleep(0.2)

    # Prometheus metrics should include utilization gauge
    # First enable prom client env
    monkeypatch.setenv("RECON_PROM_CLIENT", "1")
    m = client.get("/api/conciliacion/metrics/prom")
    assert m.status_code == 200
    text = m.data.decode("utf-8")
    assert "recon_structured_logging_async_queue_utilization" in text
