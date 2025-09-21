from backend.server import app
import time


def test_latency_utilization_and_rpm(monkeypatch):
    client = app.test_client()
    import backend.conciliacion_api as capi
    monkeypatch.setattr(capi, 'suggest_for_movement', lambda *a, **k: [])

    # Issue several suggest calls
    for _ in range(5):
        client.post('/api/conciliacion/suggest', json={'context': 'bank', 'movement_id': 11})
    metrics = client.get('/api/conciliacion/metrics').get_data(as_text=True)

    def extract(name: str, text: str):
        for line in text.splitlines():
            if line.startswith(name + ' '):
                return float(line.split()[1])
        raise AssertionError(f'metric {name} not found')

    window_size = extract('recon_suggest_latency_window_size', metrics)
    util = extract('recon_suggest_latency_window_utilization_percent', metrics)
    rpm = extract('recon_suggest_requests_per_minute', metrics)

    assert window_size >= 5
    assert util > 0
    assert rpm >= 5

    # Sleep a tiny bit to not rely on exact timing but remain <60s
    time.sleep(0.01)
    metrics2 = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    rpm2 = extract('recon_suggest_requests_per_minute', metrics2)
    # rpm can stay same or grow if other tests ran concurrently, but should be >= previous
    assert rpm2 >= rpm
