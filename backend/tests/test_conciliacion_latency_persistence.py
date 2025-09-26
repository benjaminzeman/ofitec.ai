import json
import os
import tempfile
from server import app


def test_latency_persistence_basic(monkeypatch):
    fd, path = tempfile.mkstemp(prefix='latpersist_', suffix='.json')
    os.close(fd)
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', path)
    # Reload module to trigger load (will be empty) and pick up env
    import importlib
    import conciliacion_api as capi
    importlib.reload(capi)
    monkeypatch.setattr(capi, 'suggest_for_movement', lambda *a, **k: [])
    client = app.test_client()
    for _ in range(3):
        client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 9})
    # File should exist and contain at least 3 latencies
    import time
    # Wait briefly for persistence flush (should be immediate, but be safe)
    for _ in range(10):
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                raw = fh.read().strip()
            if raw:
                data = json.loads(raw)
                break
        except FileNotFoundError:  # pragma: no cover - unlikely
            pass
        time.sleep(0.05)
    else:  # pragma: no cover - timeout
        raise AssertionError("latency persistence file remained empty")
    assert 'latencies' in data
    assert len(data['latencies']) >= 3
    # Trigger reset and ensure file updates to empty list
    monkeypatch.setenv('RECON_METRICS_RESET_TOKEN', 'tok')
    client.post('/api/conciliacion/metrics/reset', json={'token': 'tok'})
    with open(path, 'r', encoding='utf-8') as fh:
        data2 = json.load(fh)
    assert len(data2.get('latencies', [])) == 0
    # Cleanup
    os.remove(path)
