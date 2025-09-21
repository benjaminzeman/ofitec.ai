import json

from backend.server import app


def test_conciliacion_suggest_metadata(monkeypatch):
    client = app.test_client()

    # Force engine unavailable path (ensure deterministic empty suggestions)
    # by monkeypatching suggest_for_movement to raise.
    import backend.conciliacion_api as capi
    monkeypatch.setattr(capi, 'suggest_for_movement', lambda *a, **k: [])

    resp = client.post('/api/conciliacion/suggest', json={"context": "bank", "movement_id": 1, "limit": 7})
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'items' in data
    # Metadata fields should be present
    for k in ('limit_used', 'limit_min', 'limit_max', 'limit_default'):
        assert k in data
    # limit_used must respect clamps between min and max
    assert data['limit_used'] >= data['limit_min']
    assert data['limit_used'] <= data['limit_max']
    # Provided limit 7 might be clamped depending on config, just assert int
    assert isinstance(data['limit_used'], int)
