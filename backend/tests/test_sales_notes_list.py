import pytest
import server


@pytest.fixture(name='sn_client')
def _sn_client():
    server.app.config['TESTING'] = True
    with server.app.test_client() as c:
        yield c


def _create_ep(client, project_id=901):
    # Minimal EP: create header submitted + one line to allow sales note
    rv = client.post('/api/ep', json={
        'project_id': project_id,
        'period_start': '2025-09-01',
        'period_end': '2025-09-30',
        'status': 'submitted'
    })
    assert rv.status_code == 201
    ep_id = rv.get_json()['ep_id']
    rv = client.post(f'/api/ep/{ep_id}/lines/bulk', json={
        'lines': [
            {
                'item_code': 'L1',
                'qty_period': 10,
                'unit_price': 100,
                'amount_period': 1000,
            }
        ]
    })
    assert rv.status_code == 200
    return ep_id


def test_sales_notes_listing_filters(sn_client):
    ep1 = _create_ep(sn_client, project_id=910)
    ep2 = _create_ep(sn_client, project_id=911)

    # Generate two sales notes (ambas en draft inicialmente)
    r1 = sn_client.post(f'/api/ep/{ep1}/generate-sales-note')
    assert r1.status_code == 201
    sn1 = r1.get_json()['sales_note_id']
    assert r1.get_json()['status'] == 'draft'
    r2 = sn_client.post(f'/api/ep/{ep2}/generate-sales-note')
    assert r2.status_code == 201
    sn2 = r2.get_json()['sales_note_id']
    assert r2.get_json()['status'] == 'draft'

    # List all
    rv = sn_client.get('/api/sales-notes')
    assert rv.status_code == 200
    items = rv.get_json()['items']
    assert len(items) >= 2

    # Filter by ep_id
    rv = sn_client.get(f'/api/sales-notes?ep_id={ep1}')
    assert rv.status_code == 200
    items_ep1 = rv.get_json()['items']
    assert all(it['ep_id'] == ep1 for it in items_ep1)

    # Issue invoice for first EP (approve EP via dedicated endpoint first)
    approve_resp = sn_client.post(f'/api/ep/{ep1}/approve')
    assert approve_resp.status_code == 200
    # Aprobar nota antes de facturar
    ar = sn_client.post(f'/api/sales-notes/{sn1}/approve')
    assert ar.status_code == 200
    rv = sn_client.post(f'/api/sales-notes/{sn1}/issue-invoice')
    assert rv.status_code == 200

    # Cancel second note
    # Cancelar nota aún en draft debe fallar (regla nueva: solo issued)
    rv = sn_client.post(f'/api/sales-notes/{sn2}/cancel')
    assert rv.status_code == 422
    # Aprobarla y luego cancelarla
    apr2 = sn_client.post(f'/api/sales-notes/{sn2}/approve')
    assert apr2.status_code == 200
    rv = sn_client.post(f'/api/sales-notes/{sn2}/cancel')
    assert rv.status_code == 200, rv.data

    # Filter by status invoiced
    rv = sn_client.get('/api/sales-notes?status=invoiced')
    assert rv.status_code == 200
    invoiced = rv.get_json()['items']
    assert all(it['status'] == 'invoiced' for it in invoiced)

    # Filter by project_id
    rv = sn_client.get('/api/sales-notes?project_id=910')
    assert rv.status_code == 200
    proj_items = rv.get_json()['items']
    assert all(it['project_id'] == 910 for it in proj_items)

    # Invalid ep_id
    rv = sn_client.get('/api/sales-notes?ep_id=abc')
    assert rv.status_code == 400

    # Limit
    rv = sn_client.get('/api/sales-notes?limit=1')
    assert rv.status_code == 200
    assert len(rv.get_json()['items']) <= 1
