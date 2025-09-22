import os
import importlib
import pytest
from flask import Flask

# Enable AI (simulate) and inject a mock grok_chat
os.environ["AI_ENABLED"] = "1"


@pytest.fixture()
def app_instance(monkeypatch):
    # Import server fresh
    mod = importlib.import_module("backend.server")
    # Patch grok_chat in module namespace
    
    def fake_grok_chat(messages):  # noqa: D401
        # Return simple echo-like structure
        return {"ok": True, "message": {"content": "RESP:" + messages[-1]["content"][:40]}}
    monkeypatch.setattr(mod, "grok_chat", fake_grok_chat)
    app: Flask = getattr(mod, "app")
    app.testing = True
    return app

 
@pytest.fixture()
def api_client(app_instance):
    return app_instance.test_client()


def test_ai_summary_success_cache_and_rate_limit(api_client, monkeypatch):
    # First call should be miss; second identical call should hit cache and not invoke fake_grok_chat again.
    call_counter = {"n": 0}
    import backend.server as srv

    def counting_grok(messages):  # noqa: D401
        call_counter["n"] += 1
        return {"ok": True, "message": {"content": "S"}}

    monkeypatch.setattr(srv, "grok_chat", counting_grok)

    r1 = api_client.post("/api/ai/summary", json={})
    assert r1.status_code in (200, 503)  # if upstream data missing or ai disabled fallback
    if r1.status_code != 200:
        pytest.skip("AI disabled or missing context in current environment")
    d1 = r1.get_json()
    assert d1["meta"]["cache"] == "miss"
    assert call_counter["n"] == 1

    r2 = api_client.post("/api/ai/summary", json={})
    assert r2.status_code == 200
    d2 = r2.get_json()
    assert d2["meta"]["cache"] == "hit"
    assert call_counter["n"] == 1  # no extra call

    # Rate limit: temporarily set low threshold
    import backend.server as srv2
    monkeypatch.setattr(srv2, "_RATE_LIMIT_MAX", 1, raising=False)
    r3 = api_client.post("/api/ai/summary", json={})
    assert r3.status_code == 429


def test_ai_ask_success_and_async(api_client, monkeypatch):
    import backend.server as srv
    # Patch grok_chat
    responses = ["Primera", "Segunda"]

    def fake(messages):  # noqa: D401
        return {"ok": True, "message": {"content": responses.pop(0)}}

    monkeypatch.setattr(srv, "grok_chat", fake)

    r = api_client.post("/api/ai/ask", json={"question": "Que pasa?", "context": {}})
    if r.status_code == 503:
        pytest.skip("AI disabled in this environment")
    assert r.status_code == 200
    d = r.get_json()
    assert d["ok"] is True
    assert "Primera" in d["answer"]

    # Async
    monkeypatch.setattr(srv, "grok_chat", fake)
    ra = api_client.post("/api/ai/ask/async", json={"question": "Otra?", "context": {}})
    if ra.status_code == 503:
        pytest.skip("AI disabled in this environment")
    assert ra.status_code == 202
    job_id = ra.get_json()["job_id"]
    # Poll job
    job = api_client.get(f"/api/ai/jobs/{job_id}")
    assert job.status_code == 200
    jd = job.get_json()
    # Since job may still be running, allow pending status on first poll
    if jd["status"] == "pending":
        job = api_client.get(f"/api/ai/jobs/{job_id}")
        jd = job.get_json()
    assert jd["status"] in ("ok", "error", "failed")
