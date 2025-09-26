import server


def test_conciliacion_confirmar_requires_links_or_pair():
    client = server.app.test_client()
    r = client.post('/api/conciliacion/confirmar', json={"context": "bank"})
    assert r.status_code == 422
    data = r.get_json()
    assert data["error"] == "invalid_payload"
