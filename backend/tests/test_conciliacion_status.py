from backend import server


def test_conciliacion_status_basic():
    client = server.app.test_client()
    r = client.get('/api/conciliacion/status')
    assert r.status_code == 200
    data = r.get_json()
    # Core keys must be present (payload has expanded over time)
    for k in ("engine_available", "adapter_available", "version"):
        assert k in data
    assert isinstance(data["engine_available"], bool)
    assert isinstance(data["adapter_available"], bool)
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0
