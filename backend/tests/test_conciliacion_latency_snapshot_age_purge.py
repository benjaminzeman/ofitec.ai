import os
import tempfile
from server import app


def test_snapshot_age_and_purge(monkeypatch):
    fd, path = tempfile.mkstemp(prefix='latpersist_', suffix='.json')
    os.close(fd)
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', path)
    monkeypatch.setenv('RECON_METRICS_DEBUG', '1')
    monkeypatch.setenv('RECON_METRICS_DEBUG_TOKEN', 'tok')
    import importlib
    import conciliacion_api as capi
    importlib.reload(capi)
    monkeypatch.setattr(capi, 'suggest_for_movement', lambda *a, **k: [])
    client = app.test_client()
    client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 1})
    metrics = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    assert 'recon_suggest_latency_snapshot_age_seconds ' in metrics
    # Age should be >=0
    age_line = next(line for line in metrics.splitlines() if line.startswith('recon_suggest_latency_snapshot_age_seconds '))
    age_val = float(age_line.split()[-1])
    assert age_val >= 0
    # Purge without clear
    r_del = client.delete('/api/conciliacion/metrics/latencies/snapshot?token=tok')
    assert r_del.status_code == 200
    data_del = r_del.get_json()
    assert data_del['removed'] is True
    # Purge again should show removed False
    r_del2 = client.delete('/api/conciliacion/metrics/latencies/snapshot?token=tok')
    assert r_del2.status_code == 200
    data_del2 = r_del2.get_json()
    assert data_del2['removed'] is False
    # Create new samples then clear=1
    for _ in range(2):
        client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 2})
    r_del_clear = client.delete('/api/conciliacion/metrics/latencies/snapshot?token=tok&clear=1')
    assert r_del_clear.status_code == 200
    data_clear = r_del_clear.get_json()
    assert data_clear['cleared_memory'] is True
