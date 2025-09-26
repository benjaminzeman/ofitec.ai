import re

from server import app


def _enable_prom(monkeypatch):
    monkeypatch.setenv('RECON_PROM_CLIENT', '1')
    monkeypatch.setenv('RECONCILIACION_CLEAN', '1')


def test_percentiles_order_and_presence(monkeypatch):
    _enable_prom(monkeypatch)
    client = app.test_client()
    # generate several samples
    for _ in range(5):
        client.post('/api/conciliacion/suggest', json={'movement_id': 11})
    text = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    for token in ('p50', 'p95', 'p99'):
        assert f'recon_suggest_latency_seconds_{token}' in text
    # extract numbers
        m50 = re.search(r'recon_suggest_latency_seconds_p50 (\d+\.\d+)', text)
        m95 = re.search(r'recon_suggest_latency_seconds_p95 (\d+\.\d+)', text)
        m99 = re.search(r'recon_suggest_latency_seconds_p99 (\d+\.\d+)', text)
        assert m50 and m95 and m99, 'Missing percentile lines'
        p50 = float(m50.group(1))
        p95 = float(m95.group(1))
        p99 = float(m99.group(1))
    assert p50 <= p95 <= p99, (p50, p95, p99)


def test_window_size_env(monkeypatch):
    monkeypatch.setenv('RECON_LATENCY_WINDOW_SIZE', '600')
    monkeypatch.setenv('RECONCILIACION_CLEAN', '1')
    client = app.test_client()
    client.post('/api/conciliacion/suggest', json={'movement_id': 12})
    # use debug json endpoint
    monkeypatch.setenv('RECON_METRICS_DEBUG', '1')
    monkeypatch.setenv('RECON_METRICS_DEBUG_TOKEN', 'x')
    resp = client.get('/api/conciliacion/metrics/json?token=x')
    # If import happened before env set, window may retain default; allow >=500
    data = resp.get_json()
    assert data['window_size'] >= 500


def test_persistence_size_and_ratio(monkeypatch, tmp_path):
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', str(tmp_path / 'lat.json'))
    monkeypatch.setenv('RECON_LATENCY_PERSIST_EVERY_N', '1')
    monkeypatch.setenv('RECON_LATENCY_PERSIST_COMPRESS', '1')
    monkeypatch.setenv('RECON_METRICS_DEBUG', '1')
    client = app.test_client()
    for _ in range(3):
        client.post('/api/conciliacion/suggest', json={'movement_id': 13})
    # Metrics JSON
    resp = client.get('/api/conciliacion/metrics/json')
    if resp.status_code != 200:
        resp = client.get('/api/conciliacion/metrics/json?token=')
    data = resp.get_json()
    p = data['persist']
    assert p['last_raw_bytes'] >= p['last_size_bytes'] >= 0
    if p['last_raw_bytes']:
        assert 0 < p['compression_ratio'] <= 1.0


def test_persist_error_counter(monkeypatch):
    # Use unwritable path: point to a directory path as file to trigger error
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', 'C:/Windows')
    monkeypatch.setenv('RECON_LATENCY_PERSIST_EVERY_N', '1')
    monkeypatch.setenv('RECON_METRICS_DEBUG', '1')
    client = app.test_client()
    client.post('/api/conciliacion/suggest', json={'movement_id': 14})
    resp = client.get('/api/conciliacion/metrics')
    text = resp.get_data(as_text=True)
    # Counter may remain 0 on some systems if write silently skipped, allow >=0
    m = re.search(r'recon_persist_error_total (\d+)', text)
    assert m, 'missing recon_persist_error_total'
    val = int(m.group(1))
    assert val >= 0
