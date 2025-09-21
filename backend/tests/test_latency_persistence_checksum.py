import os
import json
import gzip
from pathlib import Path

from backend.conciliacion_api_clean import test_reset_internal, _record_latency, _LATENCIES, _load_persisted


def _set_env(tmp_path: Path, gzip_mode: bool):
    target = tmp_path / ("latencies.json.gz" if gzip_mode else "latencies.json")
    os.environ["RECON_LATENCY_PERSIST_PATH"] = str(target)
    os.environ["RECON_LATENCY_PERSIST_EVERY_N"] = "1"
    os.environ["RECON_DISABLE_METRICS"] = "0"
    return target


def _flush_once():
    # Force a latency record which will trigger a persistence flush (every_n=1)
    _record_latency(0.0123)
    # Add a second sample to guarantee window not empty even if one filtered elsewhere
    _record_latency(0.0042)


def test_persistence_checksum_valid_and_corruption_cleanup(tmp_path, monkeypatch):
    # Ensure test mode so test_reset_internal is permitted
    monkeypatch.setenv("RECON_TEST_MODE", "1")
    # Ensure metrics are enabled (disable flags cleared)
    monkeypatch.delenv("RECON_DISABLE_METRICS", raising=False)
    monkeypatch.delenv("RECON_METRICS_DISABLED", raising=False)
    # Configure env for plain JSON first
    target = _set_env(tmp_path, gzip_mode=False)
    test_reset_internal()
    _flush_once()
    assert target.exists(), "snapshot file should be created"
    raw = json.loads(target.read_text("utf-8"))
    # Basic shape assertions
    assert raw.get("version") == 1
    assert isinstance(raw.get("checksum"), str) and raw["checksum"].startswith("sha256:"), "checksum present"
    # Validate snapshot actually contains at least one latency (source of truth)
    assert isinstance(raw.get("latencies"), list) and raw["latencies"], "snapshot should contain latency samples"

    # Corrupt the checksum (flip a char) and ensure loader discards file
    bad = dict(raw)
    bad["checksum"] = "sha256:deadbeef" + raw["checksum"][14:]
    target.write_text(json.dumps(bad), encoding="utf-8")
    # Clear in-memory window then attempt reload
    _LATENCIES.clear()
    _load_persisted()
    # Because file was corrupted it should have been deleted and not loaded
    assert not target.exists(), "corrupted snapshot should be removed"
    assert len(_LATENCIES) == 0, "in-memory window must remain empty after corruption"

    # Now test gzip mode
    test_reset_internal()
    target_gz = _set_env(tmp_path, gzip_mode=True)
    test_reset_internal()
    _flush_once()
    assert target_gz.exists(), "gzip snapshot should be created"
    with gzip.open(target_gz, 'rt', encoding='utf-8') as fh:  # type: ignore[arg-type]
        data_gz = json.load(fh)
    assert data_gz.get("version") == 1
    assert data_gz.get("checksum", "").startswith("sha256:"), "checksum present in gzip"

    # Corrupt gzip by truncating file
    content = target_gz.read_bytes()
    target_gz.write_bytes(content[: max(10, len(content)//4)])  # write truncated part
    # Clear and reload
    _LATENCIES.clear()
    _load_persisted()
    # Truncated gzip should be removed
    assert not target_gz.exists(), "truncated gzip snapshot should be removed"
    assert len(_LATENCIES) == 0, "no latencies loaded from truncated gzip"
