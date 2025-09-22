import os
import importlib
import pytest
from flask import Flask

# Ensure no AI key present for these tests
os.environ.pop("XAI_API_KEY", None)
os.environ.pop("GROK_API_KEY", None)


@pytest.fixture(scope="module")
def app_instance():  # noqa: D401
    # Import fresh instance of server (it registers routes at import time)
    mod = importlib.import_module("backend.server")
    _app: Flask = getattr(mod, "app")
    _app.testing = True
    return _app


@pytest.fixture()
def api_client(app_instance):  # noqa: D401
    return app_instance.test_client()


def test_ai_summary_disabled(api_client):
    resp = api_client.post("/api/ai/summary", json={})
    assert resp.status_code == 503
    data = resp.get_json()
    assert data["error"] == "ai_disabled"


def test_ai_ask_missing_question(api_client):
    resp = api_client.post("/api/ai/ask", json={})
    assert resp.status_code == 422
    data = resp.get_json()
    assert data["error"] == "missing:question"
