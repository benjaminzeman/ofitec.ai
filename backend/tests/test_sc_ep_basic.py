import pytest
from backend import server


@pytest.fixture
def client():
    server.app.config['TESTING'] = True
    with server.app.test_client() as c:
        yield c


def test_sc_ep_create_lines_deductions_summary(client):
    # Ping
    rv = client.get('/api/sc/ping')
    assert rv.status_code == 200
    assert rv.get_json().get('module') == 'sc_ep'

    # Create SC EP header
    rv = client.post('/api/sc/ep', json={
        'project_id': 700,
        'subcontract_id': 55,
        'ep_number': 'SC-EP-1',
        'retention_pct': 0.08
    })
    assert rv.status_code == 201, rv.data
    ep_id = rv.get_json()['ep_id']

    # Bulk lines
    rv = client.post(
        f'/api/sc/ep/{ep_id}/lines/bulk',
        json={
            'lines': [
                {
                    'item_code': 'SC-IT-1',
                    'qty_period': 5,
                    'unit_price': 100,
                    'amount_period': 500,
                },
                {
                    'item_code': 'SC-IT-2',
                    'qty_period': 2,
                    'unit_price': 200,  # amount auto calc
                },
            ]
        },
    )
    assert rv.status_code == 200, rv.data

    # Bulk deductions
    rv = client.post(
        f'/api/sc/ep/{ep_id}/deductions/bulk',
        json={
            'deductions': [
                {
                    'type': 'retention',
                    'description': 'Retención contractual',
                    'amount': 60,
                },
                {
                    'type': 'other',
                    'description': 'Descuento menor',
                    'amount': 40,
                },
            ]
        },
    )
    assert rv.status_code == 200, rv.data

    # Get summary
    rv = client.get(f'/api/sc/ep/{ep_id}/summary')
    assert rv.status_code == 200, rv.data
    summary = rv.get_json()
    assert summary['lines_subtotal'] == 900  # 500 + (2*200)
    assert summary['deductions_total'] == 100  # 60 + 40
    assert summary['amount_net'] == 800
    # retention_computed should be None because explicit retention provided
    assert summary['retention_computed'] is None

    # List filter
    rv = client.get('/api/sc/ep?project_id=700&limit=10')
    assert rv.status_code == 200, rv.data
    items = rv.get_json()['items']
    assert any(r['id'] == ep_id for r in items)


def test_sc_ep_import_flow(client):  # noqa: F811 (reuse fixture)
    rv = client.post('/api/sc/ep/import', json={
        'header': {
            'project_id': 701,
            'ep_number': 'SC-EP-IMP-1',
            'retention_pct': 0.05
        },
        'lines': [
            {
                'item_code': 'IMP-1',
                'qty_period': 1,
                'unit_price': 1000,
                'amount_period': 1000,
            }
        ],
        'deductions': [
            {'type': 'retention', 'description': 'Retención', 'amount': 50}
        ]
    })
    assert rv.status_code == 200, rv.data
    ep_id = rv.get_json()['ep_id']

    rv = client.get(f'/api/sc/ep/{ep_id}/summary')
    assert rv.status_code == 200, rv.data
    s = rv.get_json()
    assert s['amount_net'] == 950
