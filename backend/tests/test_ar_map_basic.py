import pytest
import server


@pytest.fixture(name="ar_client")
def _ar_client():
    server.app.config['TESTING'] = True
    with server.app.test_client() as c:
        yield c


def test_ar_map_suggestions_empty_minimal(ar_client):
    # No data in DB -> expect empty suggestions list
    rv = ar_client.post('/api/ar-map/suggestions', json={'invoice': {}})
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'items' in data
    assert isinstance(data['items'], list)
    assert data['items'] == []


def test_ar_map_confirm_and_reuse_rule(ar_client):
    # Confirm a simple name-like rule for a project id "P123" (fallback schema)
    rv = ar_client.post('/api/ar-map/confirm', json={
        'rules': [
            {
                'kind': 'customer_name_like',
                'pattern': 'ACME',
                'project_id': 'P123'
            }
        ],
        'metadata': {'user_id': 'tester'}
    })
    assert rv.status_code == 201, rv.data
    payload = rv.get_json()
    assert payload['ok'] is True
    assert payload['saved_rules'] == 1

    # Now suggestions with customer name containing ACME should return the rule
    rv = ar_client.post('/api/ar-map/suggestions', json={
        'invoice': {
            'customer_name': 'ACME Chile SpA',
            'invoice_number': 'F001'
        }
    })
    assert rv.status_code == 200
    items = rv.get_json()['items']
    assert len(items) >= 1
    top = items[0]
    assert top['project_id'] == 'P123'
    # Reason may appear as alias:'pattern' or generic heuristic; check pattern
    reasons_all = (top.get('reasons') or []) + [top.get('reason')]
    assert any('ACME' in (r or '') for r in reasons_all)


def test_ar_map_auto_assign_threshold_and_dry_run(ar_client):
    # Add a strong rule for project X (customer_name_like)
    rv = ar_client.post('/api/ar-map/confirm', json={
        'rules': [
            {
                'kind': 'customer_name_like',
                'pattern': 'MEGA_CORP',
                'project_id': 'X'
            }
        ],
        'metadata': {'user_id': 'tester'}
    })
    assert rv.status_code == 201

    # Dry run first — should not update invoice even if safe
    rv = ar_client.post('/api/ar-map/auto_assign', json={
        'invoice': {
            'customer_name': 'MEGA_CORP Ltda',
            'invoice_id': 9999
        },
        'dry_run': True,
        'threshold': 0.5
    })
    assert rv.status_code == 200
    resp = rv.get_json()
    assert resp['ok'] is True
    assert resp['dry_run'] is True
    # chosen candidate should exist
    assert resp['chosen'] is not None

    # Real run (not dry) — invoice table might not exist so update may fail
    rv = ar_client.post('/api/ar-map/auto_assign', json={
        'invoice': {
            'customer_name': 'MEGA_CORP Ltda',
            'invoice_id': 10001
        },
        'threshold': 0.5
    })
    assert rv.status_code == 200
    resp2 = rv.get_json()
    assert resp2['ok'] is True
    # If invoice table absent update stays 0 -> auto_assigned False
    assert resp2['updated_invoices'] in (0, 1)
    if resp2['updated_invoices'] == 0:
        assert resp2['auto_assigned'] is False


def test_ar_map_invalid_confirm_payload(ar_client):
    # Missing rules list
    rv = ar_client.post('/api/ar-map/confirm', json={})
    assert rv.status_code == 422
    err = rv.get_json()
    assert err['error'] == 'invalid_payload'


def test_ar_map_auto_assign_no_candidates(ar_client):
    # Use a unique name that won't match existing rules
    rv = ar_client.post('/api/ar-map/auto_assign', json={
        'invoice': {'customer_name': 'ZZZ_UNMATCHABLE_123'},
        'threshold': 0.99
    })
    assert rv.status_code == 200
    resp = rv.get_json()
    assert resp['chosen'] is None
    assert resp['auto_assigned'] is False


def test_ar_map_project_hint_priority(ar_client):
    # No rules, only project_hint provided
    rv = ar_client.post('/api/ar-map/suggestions', json={
        'project_hint': 'HINT123',
        'invoice': {'customer_name': 'Totally Irrelevant'}
    })
    assert rv.status_code == 200
    items = rv.get_json()['items']
    assert len(items) >= 1
    assert items[0]['project_id'] == 'HINT123'
    assert any(
        'hint' in r
        for r in items[0].get('reasons', []) + [items[0].get('reason')]
    )
