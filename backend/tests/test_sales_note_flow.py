import pytest
from backend import server


@pytest.fixture
def client():
    server.app.config['TESTING'] = True
    with server.app.test_client() as c:
        yield c


def _create_ep_with_lines(client):
    # Contract
    rv = client.post('/api/contracts', json={
        'project_id': 777,
        'customer_id': 777,
        'code': 'CT-SN-1',
        'retention_pct': 0.05
    })
    assert rv.status_code == 200, rv.data
    cid = rv.get_json()['contract_id']
    # SOV
    rv = client.post(f'/api/contracts/{cid}/sov/import', json={
        'items': [
            {'item_code': 'IT-SN', 'qty': 1, 'unit_price': 1000}
        ]
    })
    assert rv.status_code == 200, rv.data
    # EP header
    rv = client.post('/api/ep', json={
        'project_id': 777,
        'contract_id': cid,
        'ep_number': 'EP-SN-1'
    })
    assert rv.status_code == 201, rv.data
    ep_id = rv.get_json()['ep_id']
    # Lines
    rv = client.post(f'/api/ep/{ep_id}/lines/bulk', json={
        'lines': [
            {
                'item_code': 'IT-SN',
                'qty_period': 1,
                'unit_price': 1000,
                'amount_period': 1000,
            }
        ]
    })
    assert rv.status_code == 200, rv.data
    # Approve
    rv = client.post(f'/api/ep/{ep_id}/approve')
    assert rv.status_code == 200, rv.data
    return ep_id


def test_sales_note_generate_cancel_regenerate_issue(client):
    ep_id = _create_ep_with_lines(client)
    # Generate sales note
    rv = client.post(f'/api/ep/{ep_id}/generate-sales-note')
    assert rv.status_code == 201, rv.data
    sn1 = rv.get_json()
    sid = sn1['sales_note_id']
    # Ahora debe iniciar en draft
    assert sn1['status'] == 'draft'
    # Aprobar para emitir (issued)
    rv = client.post(f'/api/sales-notes/{sid}/approve')
    assert rv.status_code == 200, rv.data
    assert rv.get_json().get('status') == 'issued'
    # Duplicate guard
    rv = client.post(f'/api/ep/{ep_id}/generate-sales-note')
    assert rv.status_code == 422, rv.data
    assert rv.get_json().get('error') == 'sales_note_exists'
    # Cancel
    rv = client.post(f'/api/sales-notes/{sid}/cancel')
    assert rv.status_code == 200, rv.data
    assert rv.get_json()['status'] == 'cancelled'
    # Regenerate (nueva nota en draft)
    rv = client.post(f'/api/ep/{ep_id}/generate-sales-note')
    assert rv.status_code == 201, rv.data
    sn2 = rv.get_json()
    assert sn2['status'] == 'draft'
    sid2 = sn2['sales_note_id']
    assert sid2 != sid
    # Aprobar segunda nota y luego emitir factura
    rv = client.post(f'/api/sales-notes/{sid2}/approve')
    assert rv.status_code == 200
    rv = client.post(f'/api/sales-notes/{sid2}/issue-invoice')
    assert rv.status_code == 200, rv.data
    invoice = rv.get_json()
    assert invoice.get('invoice_id')
    # Sales note now invoiced
    rv = client.get(f'/api/sales-notes/{sid2}')
    assert rv.status_code == 200, rv.data
    assert rv.get_json().get('status') == 'invoiced'


def test_direct_invoice_marks_sales_note(client):
    ep_id = _create_ep_with_lines(client)
    # Create sales note (draft) y aprobar antes de usar endpoint legacy
    rv = client.post(f'/api/ep/{ep_id}/generate-sales-note')
    assert rv.status_code == 201, rv.data
    sn = rv.get_json()
    sid = sn['sales_note_id']
    assert sn['status'] == 'draft'
    rv = client.post(f'/api/sales-notes/{sid}/approve')
    assert rv.status_code == 200
    # Use legacy invoice endpoint (que debe respetar estado aprobado/issued)
    rv = client.post(f'/api/ep/{ep_id}/generate-invoice')
    assert rv.status_code == 200, rv.data
    # Sales note should now be invoiced
    rv = client.get(f'/api/sales-notes/{sid}')
    assert rv.status_code == 200, rv.data
    assert rv.get_json().get('status') == 'invoiced'
