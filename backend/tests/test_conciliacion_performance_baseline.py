import os
import time
import json
import statistics
import pytest
from flask import Flask
from conciliacion_api_clean import bp as conciliacion_bp  # type: ignore

RUNTIME_MS_BUDGET = float(os.getenv("PERF_SUGGEST_P95_BUDGET_MS", "120"))  # default 120ms p95 budget
ITERATIONS = int(os.getenv("PERF_SUGGEST_ITERS", "60"))  # keep small for CI
WARMUP = int(os.getenv("PERF_SUGGEST_WARMUP", "5"))


def make_app():
    app = Flask(__name__)
    app.register_blueprint(conciliacion_bp)
    return app


@pytest.mark.perf
def test_suggest_endpoint_p95_under_budget(monkeypatch):
    if os.getenv("SKIP_PERF_TESTS") in {"1", "true", "yes"}:
        pytest.skip("Skipping perf tests via SKIP_PERF_TESTS env var")
    # Enable metrics & structured logs minimally (test mode ensures feature readiness)
    monkeypatch.setenv("RECON_TEST_MODE", "1")
    app = make_app()
    client = app.test_client()

    # Warmup
    for i in range(WARMUP):
        client.post("/api/conciliacion/suggest", json={"movement_id": i + 1, "limit": 1})

    samples = []
    for i in range(ITERATIONS):
        t0 = time.perf_counter()
        client.post("/api/conciliacion/suggest", json={"movement_id": 10_000 + i, "limit": 1})
        dt = (time.perf_counter() - t0) * 1000.0
        samples.append(dt)

    samples.sort()
    p95_index = int(len(samples) * 0.95) - 1
    p95 = samples[max(0, p95_index)]

    # Provide context if failing
    assert p95 <= RUNTIME_MS_BUDGET, f"p95 {p95:.2f}ms exceeds budget {RUNTIME_MS_BUDGET:.2f}ms (n={len(samples)})"

    # Optionally store basic stats in test report (stdout)
    mean = statistics.mean(samples)
    print(f"Perf baseline: n={len(samples)} mean={mean:.2f}ms p95={p95:.2f}ms budget={RUNTIME_MS_BUDGET:.2f}ms")

    out_path = os.getenv("PERF_BASELINE_JSON")
    if out_path:
        try:
            with open(out_path, 'w', encoding='utf-8') as fh:
                json.dump({
                    "iterations": len(samples),
                    "mean_ms": mean,
                    "p95_ms": p95,
                    "budget_ms": RUNTIME_MS_BUDGET,
                    "timestamp": time.time()
                }, fh, indent=2)
        except Exception as exc:  # pragma: no cover
            print(f"Could not write perf JSON artifact: {exc}")
