from server import app


def test_conciliacion_metrics_endpoint(monkeypatch):
    monkeypatch.setenv('RECON_METRICS_DISABLED', 'false')
    client = app.test_client()
    resp = client.get('/api/conciliacion/metrics')
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    # Basic required metrics lines
    for metric in (
        'recon_engine_available',
        'recon_adapter_available',
        'recon_alias_max_len',
        'recon_suggest_limit_min',
        'recon_suggest_limit_max',
        'recon_suggest_limit_default',
        'recon_alias_length_violation_count',
        'recon_reconciliations_total',
        'recon_links_total',
    ):
        assert metric in text
    # Prometheus format ends with newline
    assert text.endswith('\n')
