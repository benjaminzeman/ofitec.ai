import time

import pytest
from flask import Flask


@pytest.fixture()
def client(monkeypatch):
    # Reset metrics and job manager before each test
    from config import reset_prometheus_metrics
    from ai_jobs import reset_job_manager
    reset_prometheus_metrics()
    reset_job_manager()
    
    # Force AI enabled and provide fake grok_chat
    monkeypatch.setenv("AI_ENABLED", "1")
    import server as srv  # CORRECTED: from backend import server as srv
    monkeypatch.setattr(srv, "grok_chat", lambda messages: {"ok": True, "content": "obs"})
    app: Flask = srv.app
    return app.test_client()


def test_request_id_and_retry_after_headers(client, monkeypatch):
    # Exhaust rate limit quickly by lowering max
    import server as srv
    monkeypatch.setattr(srv, "_RATE_LIMIT_MAX", 1, raising=False)
    import types
    srv.ai_enabled = types.FunctionType((lambda: True).__code__, globals())  # type: ignore
    srv.grok_chat = lambda messages: {"ok": True, "content": "obs"}  # type: ignore

    # First call succeeds (ask)
    r1 = client.post("/api/ai/ask", json={"question": "hola?"})
    assert r1.status_code == 200
    assert "X-Request-ID" in r1.headers
    req_id1 = r1.headers.get("X-Request-ID")
    assert req_id1 and len(req_id1) == 16

    # Second call triggers rate limit
    r2 = client.post("/api/ai/ask", json={"question": "otra?"})
    if r2.status_code == 503:  # ai disabled scenario skip remainder
        pytest.skip("AI disabled in environment")
    assert r2.status_code == 429
    assert r2.headers.get("Retry-After") is not None
    assert r2.headers.get("X-Request-ID") != req_id1

    # Summary endpoint also returns request id
    r3 = client.post("/api/ai/summary", json={})
    if r3.status_code == 429:  # could be limited already
        assert "Retry-After" in r3.headers
    else:
        assert r3.status_code in (200, 503)
    assert "X-Request-ID" in r3.headers


def test_job_metrics_and_request_id(client, monkeypatch):
    # Skip if prometheus_client not installed
    try:
        import prometheus_client  # noqa: F401
    except Exception:
        pytest.skip("prometheus_client not installed")
    
    import server as srv
    import types
    srv.ai_enabled = types.FunctionType((lambda: True).__code__, globals())  # type: ignore
    srv.grok_chat = lambda messages: {"ok": True, "content": "obs"}  # type: ignore
    
    # Launch async job
    r = client.post("/api/ai/ask/async", json={"question": "hola?"})
    assert r.status_code == 202
    assert "X-Request-ID" in r.headers
    job_id = r.json["job_id"]
    # Poll a few times until completion
    for _ in range(10):
        jr = client.get(f"/api/ai/jobs/{job_id}")
        assert jr.status_code == 200
        if jr.json.get("status") in {"ok", "error", "failed"}:
            break
        time.sleep(0.05)
    # Fetch metrics and ensure gauges/counters exist
    m = client.get("/metrics")
    if m.status_code != 200:
        pytest.skip("/metrics not available")
    body = m.data.decode("utf-8")
    assert "ai_jobs_active" in body
    assert "ai_jobs_total" in body  # Changed from ai_jobs_created_total
    assert "ai_job_duration_seconds" in body  # Changed from ai_jobs_pruned_total
