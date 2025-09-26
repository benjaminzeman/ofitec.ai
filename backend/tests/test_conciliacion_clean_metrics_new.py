import os
import re
import json
import gzip
import tempfile
from server import app


def _fetch_metrics_text(client):
    resp = client.get('/api/conciliacion/metrics')
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def test_p95_not_below_avg_and_histogram_monotonic(monkeypatch):
    client = app.test_client()
    # generate a few samples
    for _ in range(5):
        client.post('/api/conciliacion/suggest', json={'movement_id': 1})
    text = _fetch_metrics_text(client)
    # extract avg and p95
    m_avg = re.search(r'recon_suggest_latency_seconds_avg (\d+\.\d+)', text)
    m_p95 = re.search(r'recon_suggest_latency_seconds_p95 (\d+\.\d+)', text)
    assert m_avg and m_p95, f"metrics lines missing in: {text}"
    avg = float(m_avg.group(1))
    p95 = float(m_p95.group(1))
    assert p95 >= avg, f"p95 {p95} should be >= avg {avg}"
    # histogram cumulative counts must be non-decreasing
    bucket_counts = []
    for line in text.splitlines():
        if line.startswith('recon_suggest_latency_bucket{le='):
            parts = line.rsplit(' ', 1)
            bucket_counts.append(int(parts[1]))
    assert bucket_counts == sorted(bucket_counts), f"Histogram not monotonic: {bucket_counts}"


def test_engine_ratios_sum_to_one(monkeypatch):
    client = app.test_client()
    # produce some requests (all likely empty outcome, but fine)
    for _ in range(3):
        client.post('/api/conciliacion/suggest', json={'movement_id': 2})
    text = _fetch_metrics_text(client)
    ratios = {}
    for name in ('success_ratio', 'fallback_ratio', 'error_ratio', 'empty_ratio'):
        m = re.search(rf'recon_engine_{name} (\d+\.\d+)', text)
        if m:
            ratios[name] = float(m.group(1))
    assert ratios, 'No ratios found'
    total = sum(ratios.values())
    assert abs(total - 1.0) < 1e-6, f"Ratios do not sum to 1: {ratios} (total={total})"


def test_persistence_with_compression(monkeypatch):
    fd, path = tempfile.mkstemp(prefix='recon_lat_', suffix='.json')
    os.close(fd)
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', path)
    monkeypatch.setenv('RECON_LATENCY_PERSIST_EVERY_N', '1')  # flush each sample
    monkeypatch.setenv('RECON_LATENCY_PERSIST_COMPRESS', '1')
    client = app.test_client()
    client.post('/api/conciliacion/suggest', json={'movement_id': 3})
    gz_path = path + '.gz'
    # allow a brief window for flush (should be immediate)
    for _ in range(20):
        if os.path.exists(gz_path):
            break
    assert os.path.exists(gz_path), 'Compressed persistence file not created'
    with gzip.open(gz_path, 'rt', encoding='utf-8') as fh:  # type: ignore[arg-type]
        data = json.load(fh)
    assert 'latencies' in data and len(data['latencies']) >= 1


def test_prom_endpoint_persistence_gauges(monkeypatch, tmp_path):
    monkeypatch.setenv('RECON_PROM_CLIENT', '1')
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', str(tmp_path / 'latencies.json'))
    monkeypatch.setenv('RECON_LATENCY_PERSIST_EVERY_N', '1')
    monkeypatch.setenv('RECON_LATENCY_PERSIST_COMPRESS', '1')
    monkeypatch.setenv('RECON_LATENCY_PERSIST_COMPRESS_MIN_BYTES', '512')
    client = app.test_client()
    client.post('/api/conciliacion/metrics/reset')
    client.post('/api/conciliacion/suggest', json={'movement_id': 5})
    resp = client.get('/api/conciliacion/metrics/prom')
    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_data(as_text=True)
    metrics = {}
    for line in body.splitlines():
        if not line or line.startswith('#') or '{' in line:
            continue
        name, value = line.split(' ', 1)
        metrics[name] = value.strip()
    expected = [
        'recon_persist_pending_samples',
        'recon_persist_flush_total',
        'recon_persist_last_flush_age_seconds',
        'recon_persist_force_compress',
        'recon_persist_compress_min_bytes',
    ]
    for key in expected:
        assert key in metrics, f"missing {key} in: {body}"
    assert float(metrics['recon_persist_pending_samples']) >= 0.0
    assert float(metrics['recon_persist_flush_total']) >= 1.0
    assert float(metrics['recon_persist_last_flush_age_seconds']) >= 0.0
    assert float(metrics['recon_persist_force_compress']) == 1.0
    assert float(metrics['recon_persist_compress_min_bytes']) == 512.0



def test_prom_endpoint(monkeypatch):
    monkeypatch.setenv('RECON_PROM_CLIENT', '1')
    client = app.test_client()
    # generate at least one sample
    client.post('/api/conciliacion/suggest', json={'movement_id': 4})
    resp = client.get('/api/conciliacion/metrics/prom')
    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_data(as_text=True)
    assert 'recon_suggest_latency_seconds_bucket' in body or 'recon_suggest_latency_seconds' in body
