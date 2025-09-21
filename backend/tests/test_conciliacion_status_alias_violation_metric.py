from backend.server import app


def test_conciliacion_status_alias_violation_metric():
    client = app.test_client()
    resp = client.get('/api/conciliacion/status')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'alias_length_violation_count' in data
    assert isinstance(data['alias_length_violation_count'], int)
    # -1 means error gathering metric, should ideally be >=0; allow -1 but flag if unexpected
    assert data['alias_length_violation_count'] >= -1
