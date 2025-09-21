#!/usr/bin/env python3
import unittest

class EpRetentionPartialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from backend import server
        cls.app = server.app
        cls.client = cls.app.test_client()

    def _post(self, path, payload, expected=200):
        r = self.client.post(path, json=payload)
        self.assertEqual(r.status_code, expected, r.get_data(as_text=True))
        return r.get_json()

    def test_partial_release_flow(self):
        # Contrato con 10% retención
        c = self._post(
            "/api/contracts",
            {"project_id": 33, "customer_id": 900, "code": "CT-PART", "retention_pct": 0.1},
        )
        cid = c["contract_id"]
        self._post(
            f"/api/contracts/{cid}/sov/import",
            {"items": [{"item_code": "P1", "qty": 1, "unit_price": 2000}]},
        )
        ep = self._post(
            "/api/ep",
            {"project_id": 33, "contract_id": cid, "ep_number": "EPP"},
            expected=201,
        )
        eid = ep["ep_id"]
        self._post(
            f"/api/ep/{eid}/lines/bulk",
            {"lines": [{"item_code": "P1", "qty_period": 1, "unit_price": 2000, "amount_period": 2000}]},
        )
        self._post(f"/api/ep/{eid}/approve", {})
        self._post(f"/api/ep/{eid}/generate-invoice", {})
        # Ledger inicial (esperado 200)
        led0 = self.client.get(f"/api/ep/{eid}/retention")
        self.assertEqual(led0.status_code, 200)
        held0 = led0.get_json().get("retention_held")
        self.assertEqual(held0, 200)
        # Liberar parcialmente 80
        rel_part = self._post(
            f"/api/ep/{eid}/retention/release-partial",
            {"amount": 80},
        )
        self.assertEqual(rel_part.get("released_amount"), 80)
        led1 = self.client.get(f"/api/ep/{eid}/retention")
        held1 = led1.get_json().get("retention_held")
        self.assertEqual(held1, 120)  # 200 - 80
        # Liberar resto (120) usando release total endpoint
        rel_total = self._post(
            f"/api/ep/{eid}/retention/release",
            {},
        )
        self.assertEqual(rel_total.get("released_amount"), 120)
        led2 = self.client.get(f"/api/ep/{eid}/retention")
        data2 = led2.get_json()
        self.assertEqual(data2.get("retention_held"), 0)
        self.assertEqual(data2.get("retention_released"), 200)

if __name__ == "__main__":
    unittest.main()
