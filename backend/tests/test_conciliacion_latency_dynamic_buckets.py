from backend.server import app


def test_dynamic_latency_buckets(monkeypatch):
    monkeypatch.setenv('RECON_LATENCY_BUCKETS', '0.002,0.004,0.008')
    client = app.test_client()
    # Trigger metrics without any samples
    m = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    # Should contain only configured buckets plus +Inf, not a default like 0.001 or 0.1
    assert 'recon_suggest_latency_seconds_histogram_bucket{le="0.002"}' in m
    assert 'recon_suggest_latency_seconds_histogram_bucket{le="0.004"}' in m
    assert 'recon_suggest_latency_seconds_histogram_bucket{le="0.008"}' in m
    assert 'recon_suggest_latency_seconds_histogram_bucket{le="0.001"}' not in m
    assert 'recon_suggest_latency_seconds_histogram_bucket{le="0.1"}' not in m

    # Reset endpoint should echo the parsed buckets
    monkeypatch.setenv('RECON_METRICS_RESET_TOKEN', 'tok')
    r = client.post('/api/conciliacion/metrics/reset', headers={'X-Admin-Token': 'tok'})
    assert r.status_code == 200
    data = r.get_json()
    assert data['buckets'] == [0.002, 0.004, 0.008]
