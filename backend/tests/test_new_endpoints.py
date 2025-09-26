def test_ar_map_suggestions(client):
    payload = {'invoice': {'customer_name': 'Cliente Demo'}}
    resp = client.post('/api/ar-map/suggestions', json=payload)
    assert resp.status_code == 200

def test_ar_map_confirm_validation(client):
    resp = client.post('/api/ar-map/confirm', json={'rules': []})
    assert resp.status_code == 422

def test_conciliacion_historial(client):
    resp = client.get('/api/conciliacion/historial')
    assert resp.status_code == 200
