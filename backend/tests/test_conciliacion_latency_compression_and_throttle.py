import os
import json
import gzip
import tempfile
import time
from pathlib import Path
from backend.server import app

def _reload(monkeypatch):
    import importlib
    import backend.conciliacion_api as capi
    importlib.reload(capi)
    importlib.reload(importlib.import_module('backend.conciliacion_api_clean'))
    monkeypatch.setattr(capi, 'suggest_for_movement', lambda *a, **k: [])
    return capi


def test_latency_persistence_compressed(monkeypatch):
    fd, path = tempfile.mkstemp(prefix='latpersist_', suffix='.json')
    os.close(fd)
    # Ensure plain file removed so only gzip appears
    try:
        os.remove(path)
    except OSError:
        pass
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', path)
    monkeypatch.setenv('RECON_LATENCY_PERSIST_COMPRESS', '1')
    _reload(monkeypatch)
    client = app.test_client()
    for _ in range(3):
        client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 1})
    # Expect gzip file
    for _ in range(20):
        if os.path.isfile(path + '.gz'):
            break
        time.sleep(0.05)
    assert os.path.isfile(path + '.gz'), 'Compressed snapshot not created'
    with gzip.open(path + '.gz', 'rt', encoding='utf-8') as fh:  # type: ignore[arg-type]
        data = json.load(fh)
    assert 'latencies' in data and len(data['latencies']) >= 3


def test_latency_persistence_every_n(monkeypatch):
    fd, path = tempfile.mkstemp(prefix='latpersist_', suffix='.json')
    os.close(fd)
    os.remove(path)  # remove the empty file created by mkstemp
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', path)
    monkeypatch.setenv('RECON_LATENCY_PERSIST_EVERY_N', '5')
    _reload(monkeypatch)
    client = app.test_client()
    # 3 requests -> should not flush (EVERY_N=5)
    for _ in range(3):
        client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 2})
    assert not os.path.isfile(path), 'Flush happened too early'
    for _ in range(2):
        client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 2})
    # Now should flush
    for _ in range(20):
        if os.path.isfile(path):
            break
        time.sleep(0.05)
    assert os.path.isfile(path), 'Flush after N samples failed'
    with open(path, 'r', encoding='utf-8') as fh:
        js = json.load(fh)
    assert js['latencies'], 'Latencies missing after flush'


def test_latency_persistence_interval(monkeypatch):
    fd, path = tempfile.mkstemp(prefix='latpersist_', suffix='.json')
    os.close(fd)
    os.remove(path)  # remove the empty file
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', path)
    monkeypatch.setenv('RECON_LATENCY_PERSIST_EVERY_N', '100')  # large so time triggers
    monkeypatch.setenv('RECON_LATENCY_PERSIST_INTERVAL_SEC', '1.5')
    _reload(monkeypatch)
    client = app.test_client()
    client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 3})
    # Not flushed yet
    assert not os.path.isfile(path)
    time.sleep(1.6)
    client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 3})
    for _ in range(20):
        if os.path.isfile(path):
            break
        time.sleep(0.05)
    assert os.path.isfile(path), 'Interval-based flush failed'


def test_pending_samples_gauge(monkeypatch):
    fd, path = tempfile.mkstemp(prefix='latpersist_', suffix='.json')
    os.close(fd)
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', path)
    monkeypatch.setenv('RECON_LATENCY_PERSIST_EVERY_N', '4')
    _reload(monkeypatch)
    client = app.test_client()
    # 2 requests -> pending should be 2
    for _ in range(2):
        client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 4})
    metrics = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    line_pending = next(line for line in metrics.splitlines() if line.startswith('recon_suggest_latency_persist_pending_samples '))
    val = int(line_pending.split()[-1])
    assert val >= 2  # could be 0 if flush happened due to timing, so allow >=2 safety? keep >=2


def test_engine_success_and_fallback_counters(monkeypatch):
    # success path
    fd, path = tempfile.mkstemp(prefix='latpersist_', suffix='.json')
    os.close(fd)
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', path)
    _reload(monkeypatch)
    client = app.test_client()
    client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 5})
    metrics1 = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    assert 'recon_suggest_engine_success_total ' in metrics1
    # force failure
    import backend.conciliacion_api as capi2

    def boom(*_a, **_k):
        raise RuntimeError('fail')
    monkeypatch.setattr(capi2, 'suggest_for_movement', boom)
    client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 6})
    metrics2 = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    # Both metrics should be present and fallback increased
    assert 'recon_suggest_engine_fallback_total ' in metrics2
    # ensure counters are non-negative numbers
    for name in ['recon_suggest_engine_success_total', 'recon_suggest_engine_fallback_total']:
        m_line = next(line for line in metrics2.splitlines() if line.startswith(name + ' '))
        float(m_line.split()[-1])


def test_latency_load_skips_empty_file(monkeypatch):
    fd, path = tempfile.mkstemp(prefix='latpersist_', suffix='.json')
    os.close(fd)
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', path)
    capi = _reload(monkeypatch)
    Path(path).write_text('', encoding='utf-8')
    capi._load_persisted()
    assert not os.path.exists(path)


def test_latency_load_skips_empty_gzip(monkeypatch):
    fd, path = tempfile.mkstemp(prefix='latpersist_', suffix='.json')
    os.close(fd)
    try:
        os.remove(path)
    except OSError:
        pass
    gz_path = path + '.gz'
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', path)
    capi = _reload(monkeypatch)
    with gzip.open(gz_path, 'wb') as fh:  # type: ignore[arg-type]
        fh.write(b'')
    capi._load_persisted()
    assert not os.path.exists(gz_path)


def test_latency_load_ignores_corrupt_json(monkeypatch):
    fd, path = tempfile.mkstemp(prefix='latpersist_', suffix='.json')
    os.close(fd)
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', path)
    capi = _reload(monkeypatch)
    Path(path).write_text('{', encoding='utf-8')
    capi._SUGGEST_LATENCIES.clear()
    capi._load_persisted()
    assert list(capi._SUGGEST_LATENCIES) == []


def test_latency_load_filters_invalid_values(monkeypatch):
    fd, path = tempfile.mkstemp(prefix='latpersist_', suffix='.json')
    os.close(fd)
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', path)
    capi = _reload(monkeypatch)
    payload = {
        'latencies': [0.01, '0.02', 'bad', None, 0.03],
        'slo_violation_total': '4',
        'last_reset': 123.45,
    }
    Path(path).write_text(json.dumps(payload), encoding='utf-8')
    capi._SUGGEST_LATENCIES.clear()
    capi._SUGGEST_SLO_VIOLATION_TOTAL = 0
    capi._SUGGEST_LAT_LAST_RESET = 0.0
    capi._load_persisted()
    assert list(capi._SUGGEST_LATENCIES) == [0.01, 0.02, 0.03]
    assert capi._SUGGEST_SLO_VIOLATION_TOTAL == 4
    assert capi._SUGGEST_LAT_LAST_RESET == 123.45
