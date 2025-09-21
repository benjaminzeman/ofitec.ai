from backend.server import app


def test_conciliacion_metrics_histogram_presence(monkeypatch):
    monkeypatch.setenv('RECON_METRICS_DISABLED', 'false')
    client = app.test_client()
    # Generate some latency data by monkeypatching engine to fast path
    import backend.conciliacion_api as capi
    monkeypatch.setattr(capi, 'suggest_for_movement', lambda *a, **k: [])
    for _ in range(4):
        r = client.post('/api/conciliacion/suggest', json={"context": "bank", "movement_id": 9})
        assert r.status_code == 200
    metrics = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    # Expect histogram header and at least one bucket line
    assert 'recon_suggest_latency_seconds_histogram_bucket{le="0.005"}' in metrics or 'recon_suggest_latency_seconds_histogram_bucket{le="0.01"}' in metrics
    assert 'recon_suggest_latency_seconds_histogram_bucket_total' in metrics


def test_conciliacion_metrics_reset_requires_token(monkeypatch):
    monkeypatch.setenv('RECON_METRICS_DISABLED', 'false')
    client = app.test_client()
    # Ensure token configured
    monkeypatch.setenv('RECON_METRICS_RESET_TOKEN', 'secret123')
    # Missing token
    resp = client.post('/api/conciliacion/metrics/reset')
    assert resp.status_code == 403
    # Wrong token
    resp = client.post('/api/conciliacion/metrics/reset', headers={'X-Admin-Token': 'nope'})
    assert resp.status_code == 403
    # Provide correct token
    # First create some latency entries
    import backend.conciliacion_api as capi
    monkeypatch.setattr(capi, 'suggest_for_movement', lambda *a, **k: [])
    for _ in range(2):
        client.post('/api/conciliacion/suggest', json={"context": "bank", "movement_id": 10})
    metrics_before = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    assert 'recon_suggest_latency_seconds_count 0' not in metrics_before
    reset_resp = client.post('/api/conciliacion/metrics/reset', headers={'X-Admin-Token': 'secret123'})
    assert reset_resp.status_code == 200
    data = reset_resp.get_json()
    assert data['before'] >= 1 and data['after'] == 0
    # After reset metrics summary count should be zero
    metrics_after = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    assert 'recon_suggest_latency_seconds_count 0' in metrics_after
