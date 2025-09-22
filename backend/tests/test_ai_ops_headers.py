import os
import importlib
import pytest

# Force enable AI features
os.environ["AI_ENABLED"] = "1"
os.environ.setdefault("AI_RATE_LIMIT_MAX", "3")


@pytest.fixture()
def client(monkeypatch):
    mod = importlib.import_module("backend.server")
    # Patch grok_chat to deterministic response
    
    def fake(messages):  # noqa: D401
        return {"ok": True, "content": "hola"}
    monkeypatch.setattr(mod, "grok_chat", fake)
    app = getattr(mod, "app")
    app.testing = True
    return app.test_client()


def test_summary_cache_header_and_rate_limit_headers(client):
    r1 = client.post("/api/ai/summary", json={})
    if r1.status_code == 503:
        pytest.skip("AI disabled in this environment")
    assert r1.headers.get("X-Cache") == "MISS"
    limit = int(r1.headers.get("X-RateLimit-Limit", "0"))
    assert limit >= 1
    remaining_first = int(r1.headers.get("X-RateLimit-Remaining", "0"))
    assert remaining_first <= limit
    r2 = client.post("/api/ai/summary", json={})
    assert r2.status_code == 200
    assert r2.headers.get("X-Cache") == "HIT"
    remaining_second = int(r2.headers.get("X-RateLimit-Remaining", "0"))
    assert remaining_second <= remaining_first


def test_rate_limit_exhaustion_headers(client, monkeypatch):
    # Force small window & max
    import backend.server as srv
    monkeypatch.setattr(srv, "_RATE_LIMIT_MAX", 1, raising=False)
    # first request ok
    r_ok = client.post("/api/ai/ask", json={"question": "Q?", "context": {}})
    if r_ok.status_code == 503:
        pytest.skip("AI disabled")
    # second triggers rate limit
    r_rl = client.post("/api/ai/ask", json={"question": "Q?", "context": {}})
    assert r_rl.status_code == 429
    assert r_rl.headers.get("X-RateLimit-Remaining") == "0"
    assert r_rl.headers.get("X-RateLimit-Reset") is not None


def test_job_pruning(monkeypatch):
    import backend.server as srv
    # Simulate many completed jobs
    with srv._jobs_lock:  # noqa: SLF001 (test access)
        for i in range(250):
            jid = f"job_fake_{i}"
            srv._AI_JOBS[jid] = {"id": jid, "status": "ok", "created_at": 1, "completed_at": 2}
    # Set low max and prune
    monkeypatch.setattr(srv, "_AI_JOB_MAX", 100, raising=False)
    monkeypatch.setattr(srv, "_AI_JOB_TTL_SEC", 1, raising=False)
    with srv._jobs_lock:
        srv._prune_jobs()
        assert len(srv._AI_JOBS) <= 100
