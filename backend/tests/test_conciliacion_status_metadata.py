from server import app


def test_conciliacion_status_metadata():
    client = app.test_client()
    resp = client.get('/api/conciliacion/status')
    assert resp.status_code == 200
    data = resp.get_json()
    for key in (
        'alias_max_len',
        'suggest_limit_min',
        'suggest_limit_max',
        'suggest_limit_default',
        'reconciliations_count',
        'recon_links_count',
    ):
        assert key in data, f"missing {key}"
    assert data['suggest_limit_min'] <= data['suggest_limit_default'] <= data['suggest_limit_max']
    assert isinstance(data['alias_max_len'], int) and data['alias_max_len'] > 0
    assert 'alias_length_violation_count' in data
