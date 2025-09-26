import os
import json
import gzip
import tempfile

from server import app


def test_fast_mode_every_n(monkeypatch):
    monkeypatch.setenv('RECONCILIACION_CLEAN', '1')
    monkeypatch.setenv('RECON_METRICS_DEBUG', '1')
    monkeypatch.setenv('RECON_FAST_MODE', '1')
    # Ensure base persist every n is 1 so fast mode bumps to 5
    monkeypatch.setenv('RECON_LATENCY_PERSIST_EVERY_N', '1')
    fd, path = tempfile.mkstemp(prefix='fastmode_', suffix='.json')
    os.close(fd)
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', path)
    # Import clean module (dynamic env lookups mean reload not required)
    import conciliacion_api_clean as capi  # noqa: F401
    client = app.test_client()
    for _ in range(3):
        client.post('/api/conciliacion/suggest', json={'movement_id': 100})
    # Access debug JSON
    resp = client.get('/api/conciliacion/metrics/json')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['persist']['every_n'] == 5, data['persist']


def test_alias_truncation_fields(monkeypatch):
    monkeypatch.setenv('RECONCILIACION_CLEAN', '1')
    # New isolated DB
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    tmp.close()
    monkeypatch.setenv('DB_PATH', tmp.name)
    # Long alias > 120 chars
    long_alias = 'A' * 150
    client = app.test_client()
    payload = {
        'context': 'bank',
        'confidence': 0.5,
        'metadata': {
            'alias': long_alias,
            'canonical': long_alias + '_CANON'
        },
        'links': [
            {'bank_movement_id': 1, 'sales_invoice_id': 2, 'amount': 10.0}
        ]
    }
    r = client.post('/api/conciliacion/confirmar', json=payload)
    assert r.status_code == 200, r.get_data(as_text=True)
    data = r.get_json()
    assert 'alias' in data and 'canonical' in data
    assert data['alias_truncated'] is True
    assert data['alias_original_length'] == len(long_alias)
    assert len(data['alias']) <= 120


def test_persistence_extra_fields(monkeypatch):
    monkeypatch.setenv('RECONCILIACION_CLEAN', '1')
    # Ensure fast mode does not interfere (it increases every_n flush threshold)
    monkeypatch.setenv('RECON_FAST_MODE', '0')
    monkeypatch.setenv('RECON_LATENCY_PERSIST_EVERY_N', '1')
    fd, path = tempfile.mkstemp(prefix='persist_extra_', suffix='.json')
    os.close(fd)
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', path)
    # Use existing loaded module state (no reload to avoid blueprint state drift)
    import conciliacion_api_clean as capi
    client = app.test_client()
    for _ in range(2):
        client.post('/api/conciliacion/suggest', json={'movement_id': 200})
    # Force a flush to avoid timing/order issues with every_n logic influenced by other tests
    capi._persist(force=True)
    # Read file (plain or gzip)
    if os.path.exists(path + '.gz'):
        with gzip.open(path + '.gz', 'rt', encoding='utf-8') as fh:  # type: ignore[arg-type]
            data = json.load(fh)
    else:
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
    # New fields must exist
    assert 'slo_violation_total' in data
    assert 'last_reset' in data
    assert 'window_capacity' in data


def test_metrics_new_gauges(monkeypatch):
    monkeypatch.setenv('RECONCILIACION_CLEAN', '1')
    # Force metrics enabled even if previous test set disable flag
    monkeypatch.setenv('RECON_METRICS_DISABLED', 'false')
    import conciliacion_api_clean as capi  # noqa: F401
    client = app.test_client()
    client.post('/api/conciliacion/suggest', json={'movement_id': 300})
    text = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    assert 'recon_suggest_latency_window_capacity' in text
    assert 'recon_persist_last_flush_timestamp' in text


def test_internal_reset_helper(monkeypatch):
    monkeypatch.setenv('RECONCILIACION_CLEAN', '1')
    monkeypatch.setenv('RECON_METRICS_DEBUG', '1')
    monkeypatch.setenv('RECON_TEST_MODE', '1')
    # Ensure metrics enabled overriding any previous disable flag
    monkeypatch.setenv('RECON_METRICS_DISABLED', 'false')
    client = app.test_client()
    for _ in range(4):
        client.post('/api/conciliacion/suggest', json={'movement_id': 400})
    # Ensure we have some samples
    pre = client.get('/api/conciliacion/metrics/json').get_json()['suggest_latency']['count']
    assert pre >= 1
    # Call internal helper
    import conciliacion_api_clean as capi
    capi.test_reset_internal()
    # Obtain count directly from module (bypass potential caching / debug gating)
    post = capi._latency_summary()['count']
    assert post == 0, post
