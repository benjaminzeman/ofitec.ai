import os
import time
from flask import Flask
from backend.conciliacion_api_clean import bp as conciliacion_bp  # type: ignore


def make_app():
    app = Flask(__name__)
    app.register_blueprint(conciliacion_bp)
    return app


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def test_quality_thresholds(monkeypatch):
    """Basic quality gates: failure_ratio and drop_ratio under configured limits.

    Intended for CI gating. Generates a modest number of suggest events to exercise logging.
    """
    monkeypatch.setenv("RECON_TEST_MODE", "1")
    # Force async enabled with reasonable queue to avoid artificial drops
    monkeypatch.setenv("RECON_STRUCTURED_LOG_ASYNC", "1")
    monkeypatch.setenv("RECON_STRUCTURED_LOG_ASYNC_QUEUE", "256")
    app = make_app()
    client = app.test_client()

    # Generate events
    for i in range(120):
        client.post("/api/conciliacion/suggest", json={"movement_id": 5000 + i, "limit": 1})
    # Give async thread a moment
    time.sleep(0.2)

    cfg = client.get("/api/conciliacion/logs/config").get_json()
    counters = cfg["counters"]

    failure_ratio = counters.get("failure_ratio", 0.0)
    drop_ratio = counters.get("drop_ratio", 0.0)

    max_failure = _float_env("MAX_FAILURE_RATIO", 0.02)
    max_drop = _float_env("MAX_DROP_RATIO", 0.05)

    assert failure_ratio <= max_failure, (
        f"failure_ratio {failure_ratio:.4f} exceeds limit {max_failure:.4f}"  # noqa: E501
    )
    assert drop_ratio <= max_drop, (
        f"drop_ratio {drop_ratio:.4f} exceeds limit {max_drop:.4f}"  # noqa: E501
    )
