from backend.server import app


def test_prom_extended_persistence_and_percentiles(monkeypatch, tmp_path):
    monkeypatch.setenv('RECON_PROM_CLIENT', '1')
    monkeypatch.setenv('RECONCILIACION_CLEAN', '1')
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', str(tmp_path / 'lat.json'))
    monkeypatch.setenv('RECON_LATENCY_PERSIST_EVERY_N', '1')
    monkeypatch.setenv('RECON_LATENCY_PERSIST_COMPRESS', '1')
    client = app.test_client()
    for _ in range(3):
        client.post('/api/conciliacion/suggest', json={'movement_id': 21})
    resp = client.get('/api/conciliacion/metrics/prom')
    body = resp.get_data(as_text=True)
    expected = [
        'recon_suggest_latency_p50_seconds',
        'recon_suggest_latency_p99_seconds',
        'recon_persist_last_size_bytes',
        'recon_persist_last_raw_bytes',
        'recon_persist_last_compression_ratio',
        'recon_persist_error_total',
    ]
    for k in expected:
        assert k in body, f"missing {k} in prom body"
