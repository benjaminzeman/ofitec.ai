import pytest
from backend import server


@pytest.fixture(name="client")
def _client():
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


def _create_ep_with_line(client, status="submitted", amount=1000):
    rv = client.post(
        "/api/ep",
        json={
            "project_id": 920,
            "period_start": "2025-09-01",
            "period_end": "2025-09-30",
            "status": status,
        },
    )
    assert rv.status_code == 201
    ep_id = rv.get_json()["ep_id"]
    if amount:
        rv = client.post(
            f"/api/ep/{ep_id}/lines/bulk",
            json={
                "lines": [
                    {
                        "item_code": "X",
                        "qty_period": 10,
                        "unit_price": amount / 10,
                        "amount_period": amount,
                    }
                ]
            },
        )
        assert rv.status_code == 200
    return ep_id


def test_invoice_from_sales_note_without_approval(client):
    ep_id = _create_ep_with_line(client, status="submitted")
    # generate sales note (allowed in submitted)
    r = client.post(f"/api/ep/{ep_id}/generate-sales-note")
    assert r.status_code == 201
    sid = r.get_json()["sales_note_id"]
    # attempt invoice without approval -> 422 invalid_state (unchanged intent)
    resp = client.post(f"/api/sales-notes/{sid}/issue-invoice")
    assert resp.status_code == 422
    data = resp.get_json()
    assert data["error"] == "invalid_state"
    # aprobar y volver a intentar debe permitir si EP aprobado
    aep = client.post(f"/api/ep/{ep_id}/approve")
    assert aep.status_code == 200
    apr = client.post(f"/api/sales-notes/{sid}/approve")
    assert apr.status_code == 200
    inv_ok = client.post(f"/api/sales-notes/{sid}/issue-invoice")
    assert inv_ok.status_code == 200


def test_cancel_after_invoiced_sales_note(client):
    ep_id = _create_ep_with_line(client, status="submitted")
    r = client.post(f"/api/ep/{ep_id}/generate-sales-note")
    assert r.status_code == 201
    sid = r.get_json()["sales_note_id"]
    # approve EP and sales note then invoice via sales note
    a = client.post(f"/api/ep/{ep_id}/approve")
    assert a.status_code == 200
    apr = client.post(f"/api/sales-notes/{sid}/approve")
    assert apr.status_code == 200
    inv = client.post(f"/api/sales-notes/{sid}/issue-invoice")
    assert inv.status_code == 200
    # try cancel -> 422 invalid_state (invoiced can't cancel)
    c = client.post(f"/api/sales-notes/{sid}/cancel")
    assert c.status_code == 422
    cerr = c.get_json()
    assert cerr["error"] == "invalid_state"


def test_zero_amount_sales_note(client):
    # Create EP with no lines so subtotal=0
    ep_id = _create_ep_with_line(client, status="submitted", amount=0)
    # Try generate sales note -> 422 zero_amount_sales_note
    r = client.post(f"/api/ep/{ep_id}/generate-sales-note")
    assert r.status_code == 422
    data = r.get_json()
    assert data["error"] == "zero_amount_sales_note"
