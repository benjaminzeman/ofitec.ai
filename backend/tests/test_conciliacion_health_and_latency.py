from backend.server import app


def test_conciliacion_healthz():
    client = app.test_client()
    r = client.get('/api/conciliacion/healthz')
    assert r.status_code == 200
    assert r.get_json() == {"ok": True}


def test_conciliacion_latency_metrics_after_suggest(monkeypatch):
    client = app.test_client()

    # Monkeypatch suggest_for_movement to ensure deterministic quick path
    import backend.conciliacion_api as capi
    monkeypatch.setattr(capi, 'suggest_for_movement', lambda *a, **k: [])

    # Call suggest a few times to populate latency deque
    for _ in range(3):
        resp = client.post('/api/conciliacion/suggest', json={"context": "bank", "movement_id": 1})
        assert resp.status_code == 200

    # Fetch metrics and assert latency summary fields exist
    metrics = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    for m in (
        'recon_suggest_latency_seconds_count',
        'recon_suggest_latency_seconds_sum',
        'recon_suggest_latency_seconds_avg',
        'recon_suggest_latency_seconds_p95',
    ):
        assert m in metrics
    # Count should be >= number of calls we made (exact equality acceptable)
    # Here we at least ensure non-zero
    assert 'recon_suggest_latency_seconds_count 0' not in metrics
