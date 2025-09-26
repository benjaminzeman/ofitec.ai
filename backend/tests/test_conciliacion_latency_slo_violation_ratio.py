from server import app


def test_slo_violation_ratio_and_total(monkeypatch):
    # Configure extremely low SLO so every sample violates
    monkeypatch.setenv('RECON_LATENCY_SLO_P95', '0.0000001')
    monkeypatch.setenv('RECON_METRICS_DEBUG', '1')
    import conciliacion_api as capi
    # Force suggest to be fast returning empty list
    monkeypatch.setattr(capi, 'suggest_for_movement', lambda *a, **k: [])
    client = app.test_client()
    # Generate 5 samples
    for _ in range(5):
        client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 123})
    metrics = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    assert 'recon_suggest_latency_p95_violation_ratio ' in metrics
    # Ratio should be > 0 (likely 1.0) since all > tiny SLO
    # Extract ratio line
    ratio_line = next(line for line in metrics.splitlines() if line.startswith('recon_suggest_latency_p95_violation_ratio '))
    ratio_value = float(ratio_line.split()[-1])
    assert ratio_value > 0.0
    total_line = next(line for line in metrics.splitlines() if line.startswith('recon_suggest_latency_p95_violation_total '))
    total_value = int(float(total_line.split()[-1]))
    assert total_value >= 5  # all samples should have counted

    # Reset metrics and ensure cumulative counter resets
    monkeypatch.setenv('RECON_METRICS_RESET_TOKEN', 'tok')
    r_reset = client.post('/api/conciliacion/metrics/reset', json={'token': 'tok'})
    assert r_reset.status_code == 200
    data_reset = r_reset.get_json()
    assert data_reset['slo_violation_total_before'] == total_value
    assert data_reset['slo_violation_total_after'] == 0


def test_debug_token_required(monkeypatch):
    monkeypatch.setenv('RECON_METRICS_DEBUG', '1')
    monkeypatch.setenv('RECON_METRICS_DEBUG_TOKEN', 'secdebug')
    import conciliacion_api as capi
    monkeypatch.setattr(capi, 'suggest_for_movement', lambda *a, **k: [])
    client = app.test_client()
    # Fire one sample
    client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 55})
    # Missing token -> 403
    r_forbidden = client.get('/api/conciliacion/metrics/latencies')
    assert r_forbidden.status_code == 403
    # Provide token via header
    r_ok = client.get('/api/conciliacion/metrics/latencies', headers={'X-Admin-Token': 'secdebug'})
    assert r_ok.status_code == 200
    # Provide token via query parameter also works
    r_ok_q = client.get('/api/conciliacion/metrics/latencies?token=secdebug')
    assert r_ok_q.status_code == 200
