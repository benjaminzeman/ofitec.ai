from backend import server


def test_admin_routes_contains_key_endpoints():
    client = server.app.test_client()
    r = client.get('/api/admin/routes')
    assert r.status_code == 200
    data = r.get_json()
    rules = {rt['rule'] for rt in data['routes']}
    # Minimal smoke: sales invoices, conciliacion status & confirmar endpoints
    assert '/api/sales_invoices' in rules
    assert '/api/conciliacion/status' in rules
    assert '/api/conciliacion/confirmar' in rules
