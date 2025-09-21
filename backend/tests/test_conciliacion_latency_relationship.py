from backend.server import app


def test_conciliacion_latency_relationship(monkeypatch):
    client = app.test_client()
    import backend.conciliacion_api as capi
    monkeypatch.setattr(capi, 'suggest_for_movement', lambda *a, **k: [])

    for _ in range(5):
        r = client.post('/api/conciliacion/suggest', json={"context": "bank", "movement_id": 123})
        assert r.status_code == 200

    metrics = client.get('/api/conciliacion/metrics').get_data(as_text=True)
    # Extract simple numeric values
    
    def _extract(name: str) -> float:
        for line in metrics.splitlines():
            if line.startswith(name + ' '):
                return float(line.split()[1])
        raise AssertionError(f"metric {name} not found")

    count = _extract('recon_suggest_latency_seconds_count')
    total = _extract('recon_suggest_latency_seconds_sum')
    avg = _extract('recon_suggest_latency_seconds_avg')
    p95 = _extract('recon_suggest_latency_seconds_p95')

    assert count >= 5
    if count > 0:
        # Basic consistency: avg = total / count (allow tiny float drift)
        assert abs(avg - (total / count)) < 1e-6 or total == 0
        # p95 should be >= avg
    assert p95 >= avg
