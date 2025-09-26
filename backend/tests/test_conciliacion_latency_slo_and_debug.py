from server import app


def test_latency_slo_gauges(monkeypatch):
    monkeypatch.setenv('RECON_LATENCY_SLO_P95', '0.000001')  # tiny slo to trigger violation after samples
    client = app.test_client()
    import conciliacion_api as capi
    monkeypatch.setattr(capi, 'suggest_for_movement', lambda *a, **k: [])
    for _ in range(2):
        client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 77})
    metrics = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    assert 'recon_suggest_latency_p95_slo ' in metrics
    assert 'recon_suggest_latency_p95_violation ' in metrics


def test_latency_debug_endpoint(monkeypatch):
    client = app.test_client()
    # Disabled by default
    r_disabled = client.get('/api/conciliacion/metrics/latencies')
    assert r_disabled.status_code == 404
    # Enable debug
    monkeypatch.setenv('RECON_METRICS_DEBUG', '1')
    import conciliacion_api as capi
    monkeypatch.setattr(capi, 'suggest_for_movement', lambda *a, **k: [])
    for _ in range(3):
        client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 88})
    r_all = client.get('/api/conciliacion/metrics/latencies')
    assert r_all.status_code == 200
    data_all = r_all.get_json()
    assert data_all['count'] >= 3
    # Limit param
    r_limited = client.get('/api/conciliacion/metrics/latencies?limit=2')
    assert r_limited.status_code == 200
    data_lim = r_limited.get_json()
    assert data_lim['count'] == 2
