import os
import tempfile
from backend.server import app


def test_persistence_file_size_gauge_and_snapshot(monkeypatch):
    fd, path = tempfile.mkstemp(prefix='latpersist_', suffix='.json')
    os.close(fd)
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', path)
    monkeypatch.setenv('RECON_METRICS_DEBUG', '1')
    monkeypatch.setenv('RECON_METRICS_DEBUG_TOKEN', 'tok')
    import importlib
    import backend.conciliacion_api as capi
    importlib.reload(capi)
    monkeypatch.setattr(capi, 'suggest_for_movement', lambda *a, **k: [])
    client = app.test_client()
    for _ in range(4):
        client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 77})
    metrics = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    # Gauge should appear
    assert 'recon_suggest_latency_persist_file_bytes ' in metrics
    # Snapshot endpoint with token
    snap = client.get('/api/conciliacion/metrics/latencies/snapshot?token=tok')
    assert snap.status_code == 200
    payload = snap.get_json()
    assert 'latencies' in payload and len(payload['latencies']) >= 4
    assert payload.get('version') == 1
    # Remove file then snapshot falls back to live source
    os.remove(path)
    snap2 = client.get('/api/conciliacion/metrics/latencies/snapshot?token=tok')
    assert snap2.status_code == 200
    payload2 = snap2.get_json()
    assert payload2.get('source') == 'live'
