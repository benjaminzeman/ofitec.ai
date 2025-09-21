def test_metrics_disabled_toggle(monkeypatch):
    import os
    os.environ['RECON_DISABLE_METRICS'] = '1'
    from backend.server import app
    client = app.test_client()
    # /metrics should 404
    r = client.get('/api/conciliacion/metrics')
    assert r.status_code == 404
    # /metrics/reset should also 404 even if token provided
    monkeypatch.setenv('RECON_METRICS_RESET_TOKEN', 'x')
    r2 = client.post('/api/conciliacion/metrics/reset', headers={'X-Admin-Token': 'x'})
    assert r2.status_code == 404
    # /status should still work
    s = client.get('/api/conciliacion/status')
    assert s.status_code == 200
