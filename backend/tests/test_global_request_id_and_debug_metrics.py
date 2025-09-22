import importlib
from flask import Flask


def test_global_request_id_on_non_ai_endpoint(monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "0")  # ensure AI can be disabled; request ID still present
    srv = importlib.reload(importlib.import_module("backend.server"))
    app: Flask = srv.app
    client = app.test_client()
    # Use a generic path likely to exist; fallback to root if 404
    resp = client.get("/")
    # Some apps may not define root; if 404 still should have header
    assert "X-Request-ID" in resp.headers
    rid = resp.headers.get("X-Request-ID")
    assert rid and len(rid) == 16


def test_ai_metrics_debug_endpoint(monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "1")
    srv = importlib.reload(importlib.import_module("backend.server"))
    app: Flask = srv.app
    client = app.test_client()
    r = client.get("/api/ai/metrics/debug")
    assert r.status_code == 200
    data = r.get_json()
    assert "metrics_enabled" in data
    assert "jobs" in data and isinstance(data["jobs"], dict)
    assert "active" in data["jobs"]
    # Header should be present globally
    assert "X-Request-ID" in r.headers
