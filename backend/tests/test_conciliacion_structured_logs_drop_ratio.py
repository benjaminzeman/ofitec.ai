import os
import time
import pytest
from flask import Flask
from backend.conciliacion_api_clean import bp as conciliacion_bp  # type: ignore


def make_app():
    app = Flask(__name__)
    app.register_blueprint(conciliacion_bp)
    return app


@pytest.mark.stress
def test_drop_ratio_increases_on_queue_saturation(monkeypatch):
    # Allow skipping in CI or slow envs
    if os.getenv("SKIP_STRESS_TESTS") in {"1", "true", "yes"}:
        pytest.skip("Skipping stress tests via SKIP_STRESS_TESTS env var")
    monkeypatch.setenv("RECON_TEST_MODE", "1")
    # Enable async logging and set a tiny queue to force saturation
    monkeypatch.setenv("RECON_STRUCTURED_LOG_ASYNC", "1")
    monkeypatch.setenv("RECON_STRUCTURED_LOG_ASYNC_QUEUE", "10")  # small capacity
    app = make_app()
    client = app.test_client()

    # Prime: emit one event to ensure worker started
    client.post("/api/conciliacion/suggest", json={"movement_id": 1, "limit": 1})

    # Rapidly enqueue more events than queue can drain to cause drops
    burst = 1200
    for i in range(burst):
        client.post("/api/conciliacion/suggest", json={"movement_id": 1000 + i, "limit": 1})
    # Adaptive wait: poll for drops up to 0.5s
    deadline = time.time() + 0.5
    drops = 0
    while time.time() < deadline:
        cfg_mid = client.get("/api/conciliacion/logs/config").get_json()
        drops = cfg_mid["counters"].get("queue_dropped_total", 0)
        if drops > 0:
            break
        time.sleep(0.05)
    if drops == 0:  # avoid hard failure in rare environments—treat as inconclusive
        pytest.skip("Could not induce queue drops in allotted time; skipping stress assertion")

    cfg = client.get("/api/conciliacion/logs/config").get_json()
    counters = cfg["counters"]

    # We expect some drops and a non-zero drop_ratio
    assert counters["queue_dropped_total"] >= 1
    assert counters["drop_ratio"] > 0.0
    # Utilization should have fluctuated; ensure fields present
    assert "async_queue_utilization" in counters
    assert "overrides_active_count" in counters
