import pytest
from backend import server


@pytest.fixture
def client():
    server.app.config['TESTING'] = True
    with server.app.test_client() as c:
        yield c

@pytest.fixture
def prepared_invoice(client):
    # Contract + SOV
    rv = client.post('/api/contracts', json={
        'project_id': 901,
        'customer_id': 901,
        'code': 'CT-AR-1'
    })
    assert rv.status_code == 200, rv.data
    cid = rv.get_json()['contract_id']
    rv = client.post(f'/api/contracts/{cid}/sov/import', json={
        'items': [
            {'item_code': 'IT-AR', 'qty': 1, 'unit_price': 1000}
        ]
    })
    assert rv.status_code == 200, rv.data
    # EP header + line
    rv = client.post('/api/ep', json={
        'project_id': 901,
        'contract_id': cid,
        'ep_number': 'EP-AR-1'
    })
    assert rv.status_code == 201, rv.data
    ep_id = rv.get_json()['ep_id']
    rv = client.post(f'/api/ep/{ep_id}/lines/bulk', json={
        'lines': [
            {
                'item_code': 'IT-AR',
                'qty_period': 1,
                'unit_price': 1000,
                'amount_period': 1000,
            }
        ]
    })
    assert rv.status_code == 200, rv.data
    rv = client.post(f'/api/ep/{ep_id}/approve')
    assert rv.status_code == 200, rv.data
    rv = client.post(f'/api/ep/{ep_id}/generate-invoice')
    assert rv.status_code == 200, rv.data
    invoice = rv.get_json()
    return invoice


def test_ar_collections_partial_full_and_guard(client, prepared_invoice):
    inv_id = prepared_invoice.get('invoice_id') or prepared_invoice.get('id')
    total = (
        prepared_invoice.get('amount_total')
        or prepared_invoice.get('total')
    )
    assert inv_id and total
    # Partial collection
    rv = client.post(
        f'/api/ar/invoices/{inv_id}/collect',
        json={'amount': total / 2},
    )
    assert rv.status_code == 200, rv.data
    # Second partial (rest) -> should mark paid
    rv = client.post(
        f'/api/ar/invoices/{inv_id}/collect',
        json={'amount': total - total / 2},
    )
    assert rv.status_code == 200, rv.data
    # Over collect attempt
    rv = client.post(f'/api/ar/invoices/{inv_id}/collect', json={'amount': 1})
    assert rv.status_code == 422, rv.data
    payload = rv.get_json()
    assert payload.get('error') == 'over_collected'
