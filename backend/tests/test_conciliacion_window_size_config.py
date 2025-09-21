import importlib


def test_window_size_config_reload(monkeypatch):
    monkeypatch.setenv('RECON_LATENCY_WINDOW_SIZE', '900')
    monkeypatch.setenv('RECONCILIACION_CLEAN', '1')
    import backend.conciliacion_api_clean as mod
    importlib.reload(mod)
    assert mod._LATENCIES.maxlen == 900  # type: ignore[attr-defined]
