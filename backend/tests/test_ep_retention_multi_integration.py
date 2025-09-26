import pytest
import server


@pytest.fixture
def client():
    server.app.config['TESTING'] = True
    with server.app.test_client() as c:
        yield c


def _create_contract(client, code, retention_pct=0.1):
    rv = client.post('/api/contracts', json={
        'project_id': 900,
        'customer_id': 900,
        'code': code,
        'retention_pct': retention_pct
    })
    assert rv.status_code == 200, rv.data
    return rv.get_json()['contract_id']


def _import_sov(client, contract_id):
    # Provide SOV with total qty 6 @ 1000/6 each simplified as lines that allow
    # subsequent EPs to book incremental progress without exceeding caps.
    rv = client.post(
        f'/api/contracts/{contract_id}/sov/import',
        json={
            'items': [
                # Model value 6000 as qty 6 * 1000 each.
                # Later EP lines consume cumulative qty <= 6.
                {'item_code': 'IT-MULTI', 'qty': 6, 'unit_price': 1000}
            ]
        },
    )
    assert rv.status_code == 200, rv.data


def _create_ep(client, contract_id, ep_number, qty=1, price=1000):
    rv = client.post('/api/ep', json={
        'project_id': 900,
        'contract_id': contract_id,
        'ep_number': ep_number
    })
    assert rv.status_code == 201, rv.data
    ep_id = rv.get_json()['ep_id']
    rv = client.post(f'/api/ep/{ep_id}/lines/bulk', json={
        'lines': [
            {
                'item_code': 'IT-MULTI',
                'qty_period': qty,
                'unit_price': price,
                'amount_period': qty * price,
            }
        ]
    })
    assert rv.status_code == 200, rv.data
    rv = client.post(f'/api/ep/{ep_id}/approve')
    assert rv.status_code == 200, rv.data
    return ep_id


def _generate_invoice(client, ep_id):
    rv = client.post(f'/api/ep/{ep_id}/generate-invoice')
    assert rv.status_code == 200, rv.data
    return rv.get_json()['invoice_id']


def _ledger(client, ep_id):
    # Use summary endpoint which computes retention aggregates
    rv = client.get(f'/api/ep/{ep_id}/summary')
    assert rv.status_code == 200, rv.data
    data = rv.get_json()
    return data['retention_held'], data['retention_released']


def test_multi_ep_retention_flow(client):
    contract_id = _create_contract(client, 'CT-MULTI', retention_pct=0.1)
    _import_sov(client, contract_id)

    # Create three EPs with different amounts
    # Additive qty so total qty <= 6 (SOV cap); constant unit_price.
    ep1 = _create_ep(
        client, contract_id, 'EP-MULTI-1', qty=1, price=1000
    )  # amount 1000 retention 100
    ep2 = _create_ep(
        client, contract_id, 'EP-MULTI-2', qty=2, price=1000
    )  # amount 2000 retention 200
    ep3 = _create_ep(
        client, contract_id, 'EP-MULTI-3', qty=3, price=1000
    )  # amount 3000 retention 300

    _generate_invoice(client, ep1)
    _generate_invoice(client, ep2)
    _generate_invoice(client, ep3)

    held1, released1 = _ledger(client, ep1)
    held2, released2 = _ledger(client, ep2)
    held3, released3 = _ledger(client, ep3)

    assert released1 == 0 and released2 == 0 and released3 == 0
    assert held1 == 100 and held2 == 200 and held3 == 300

    # Full release EP1 retention
    rv = client.post(f'/api/ep/{ep1}/retention/release', json={'mode': 'full'})
    assert rv.status_code == 200, rv.data
    held1_after, released1_after = _ledger(client, ep1)
    assert held1_after == 0 and released1_after == 100

    # (Partial release not supported yet) perform full release EP3
    rv = client.post(f'/api/ep/{ep3}/retention/release', json={'mode': 'full'})
    assert rv.status_code == 200, rv.data
    held3_final, released3_final = _ledger(client, ep3)
    assert held3_final == 0 and released3_final == 300

    # EP2 still fully held; now full release
    rv = client.post(f'/api/ep/{ep2}/retention/release', json={'mode': 'full'})
    assert rv.status_code == 200, rv.data
    held2_final, released2_final = _ledger(client, ep2)
    assert held2_final == 0 and released2_final == 200
