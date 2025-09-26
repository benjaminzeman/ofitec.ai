import pytest
import server


@pytest.fixture
def client():
    server.app.config['TESTING'] = True
    with server.app.test_client() as c:
        yield c


def test_ap_match_feedback_accept_and_reject(client):
    # Accept feedback
    rv = client.post('/api/ap-match/feedback', json={
        'invoice_id': 12345,
        'accepted': True,
        'reason': 'auto-accept test',
        'user_id': 'tester'
    })
    assert rv.status_code == 200, rv.data
    data_ok = rv.get_json()
    assert data_ok['ok'] is True
    assert data_ok['accepted'] == 1

    # Reject feedback
    rv = client.post('/api/ap-match/feedback', json={
        'invoice_id': 12345,
        'accepted': False,
        'reason': 'reject test',
        'user_id': 'tester'
    })
    assert rv.status_code == 200, rv.data
    data_rej = rv.get_json()
    assert data_rej['ok'] is True
    assert data_rej['accepted'] == 0


def test_ap_match_feedback_missing_invoice(client):
    rv = client.post('/api/ap-match/feedback', json={
        'accepted': True
    })
    assert rv.status_code == 422, rv.data
    payload = rv.get_json()
    assert payload.get('error') == 'invoice_id_required'
