from backend.server import app


def test_latency_window_and_reset_metrics(monkeypatch):
    client = app.test_client()
    import backend.conciliacion_api as capi
    monkeypatch.setattr(capi, 'suggest_for_movement', lambda *a, **k: [])

    # initial metrics capture
    m_initial = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    assert 'recon_suggest_latency_last_reset_timestamp' in m_initial
    assert 'recon_suggest_latency_window_size' in m_initial

    # generate some samples
    for _ in range(3):
        client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 1})
    m_after = client.get('/api/conciliacion/metrics').get_data(as_text=True)

    def extract(name: str, text: str):
        for line in text.splitlines():
            if line.startswith(name + ' '):
                return float(line.split()[1])
        raise AssertionError(f'metric {name} not found')

    size_after = extract('recon_suggest_latency_window_size', m_after)
    assert size_after >= 3

    # Reset metrics
    monkeypatch.setenv('RECON_METRICS_RESET_TOKEN', 'zzz')
    r = client.post('/api/conciliacion/metrics/reset', headers={'X-Admin-Token': 'zzz'})
    assert r.status_code == 200
    data = r.get_json()
    assert data['after'] == 0
    # After reset size should be 0
    m_reset = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    size_post_reset = extract('recon_suggest_latency_window_size', m_reset)
    assert size_post_reset == 0
