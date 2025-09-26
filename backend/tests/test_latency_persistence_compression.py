import json
import gzip
import time
from pathlib import Path

from conciliacion_api_clean import _record_latency, _load_persisted


def test_latency_persistence_gzip_threshold(tmp_path, monkeypatch):
    # Force a very low threshold to guarantee gzip usage when size grows
    snap = tmp_path / 'latencies.json'
    monkeypatch.setenv('RECON_LATENCY_PERSIST_PATH', str(snap))
    monkeypatch.setenv('RECON_LATENCY_PERSIST_COMPRESS_MIN_BYTES', '1')  # any payload >1B triggers
    monkeypatch.setenv('RECON_LATENCY_PERSIST_EVERY_N', '3')  # flush after 3 samples
    # Ensure force flag off so we test threshold path
    monkeypatch.delenv('RECON_LATENCY_PERSIST_COMPRESS', raising=False)

    # Generate a few samples ( > every_n )
    for _ in range(3):
        _record_latency(0.01)
        time.sleep(0.001)

    # There should be a gzip file (either original path + .gz or if path itself ended with .gz)
    gz_path = Path(str(snap) + '.gz')
    assert gz_path.exists(), 'Expected compressed snapshot .gz not found'

    # Validate JSON contents inside gzip
    with gzip.open(gz_path, 'rt', encoding='utf-8') as fh:  # type: ignore[arg-type]
        data = json.load(fh)
    assert 'latencies' in data and isinstance(data['latencies'], list)
    assert len(data['latencies']) >= 3
    # Loader should not raise
    _load_persisted()
