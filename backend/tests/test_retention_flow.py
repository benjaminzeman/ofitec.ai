import pytest
from backend import server


@pytest.fixture(name="client")
def _client():
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


def _ep_with_amount(client, amount=1000, retention_pct=0.1):
    rv = client.post(
        "/api/ep",
        json={
            "project_id": 930,
            "period_start": "2025-09-01",
            "period_end": "2025-09-30",
            "status": "submitted",
            "retention_pct": retention_pct,
        },
    )
    assert rv.status_code == 201
    ep_id = rv.get_json()["ep_id"]
    rv = client.post(
        f"/api/ep/{ep_id}/lines/bulk",
        json={
            "lines": [
                {
                    "item_code": "R1",
                    "qty_period": 10,
                    "unit_price": amount / 10,
                    "amount_period": amount,
                }
            ]
        },
    )
    assert rv.status_code == 200
    # approve then invoice directly (triggers retention ledger)
    a = client.post(f"/api/ep/{ep_id}/approve")
    assert a.status_code == 200
    inv = client.post(f"/api/ep/{ep_id}/generate-invoice")
    assert inv.status_code == 200
    return ep_id, inv.get_json()["invoice_id"]


def test_retention_ledger_and_full_release(client):
    ep_id, _ = _ep_with_amount(client)
    # fetch retention summary
    r = client.get(f"/api/ep/{ep_id}/retention")
    assert r.status_code == 200
    data = r.get_json()
    assert data["retention_held"] > 0
    outstanding = data["retention_outstanding"]
    # full release
    rel = client.post(
        f"/api/ep/{ep_id}/retention/release", json={"amount": outstanding}
    )
    assert rel.status_code == 200
    rel_data = rel.get_json()
    assert rel_data["released_amount"] == pytest.approx(outstanding, rel=1e-6)
    # second release attempt -> 422 invalid_state
    again = client.post(f"/api/ep/{ep_id}/retention/release")
    assert again.status_code == 422
    assert again.get_json()["error"] == "invalid_state"
    
def test_retention_partial_release(client):
    ep_id, _ = _ep_with_amount(client, amount=2000, retention_pct=0.05)
    r = client.get(f"/api/ep/{ep_id}/retention")
    held = r.get_json()["retention_held"]
    # partial: release half
    half = round(held / 2, 2)
    pr = client.post(
        f"/api/ep/{ep_id}/retention/release-partial",
        json={"amount": half},
    )
    assert pr.status_code == 200
    pr_data = pr.get_json()
    assert pr_data["released_amount"] == pytest.approx(half, rel=1e-6)
    # after partial release, remaining outstanding should decrease
    after = client.get(f"/api/ep/{ep_id}/retention").get_json()
    assert after["retention_outstanding"] == pytest.approx(
        held - half, rel=1e-6
    )
    # attempt partial exceeding outstanding
    exceed = client.post(
        f"/api/ep/{ep_id}/retention/release-partial",
        json={"amount": held * 2},
    )
    assert exceed.status_code == 422
    assert exceed.get_json()["error"] == "amount_exceeds_outstanding"
