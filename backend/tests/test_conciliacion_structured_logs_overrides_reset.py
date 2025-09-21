import time
from flask import Flask
from backend.conciliacion_api_clean import bp as conciliacion_bp  # type: ignore


def make_app():
    app = Flask(__name__)
    app.register_blueprint(conciliacion_bp)
    return app


def test_override_reset_and_gauges(monkeypatch):
    monkeypatch.setenv("RECON_TEST_MODE", "1")
    monkeypatch.setenv("RECON_PROM_CLIENT", "1")
    app = make_app()
    client = app.test_client()

    # Apply overrides
    r1 = client.post("/api/conciliacion/logs/runtime", json={
        "global_sample_rate": 0.5,
        "async_enabled": True,
        "per_event_sample": {"recon_suggest_request": 0.8}
    })
    assert r1.status_code == 200

    # Trigger events
    for i in range(5):
        client.post("/api/conciliacion/suggest", json={"movement_id": i+1, "limit": 1})
    time.sleep(0.2)

    # Metrics with overrides should show overrides_active_count > 0
    prom = client.get("/api/conciliacion/metrics/prom")
    text = prom.data.decode("utf-8")
    assert "recon_structured_logging_overrides_active_count" in text

    # Reset overrides
    rdel = client.delete("/api/conciliacion/logs/runtime")
    assert rdel.status_code == 200
    assert rdel.get_json()["cleared"] is True

    # Config should now show no runtime_overrides
    cfg = client.get("/api/conciliacion/logs/config")
    cfgj = cfg.get_json()
    assert cfgj["runtime_overrides"] == {}

    # Drop ratio gauge presence (always present, may be 0)
    assert "recon_structured_logging_drop_ratio" in text
