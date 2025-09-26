#!/usr/bin/env python3
import unittest

class EpRetentionModesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import server
        cls.app = server.app
        cls.client = cls.app.test_client()

    def _post(self, path, payload, expected=200):
        r = self.client.post(path, json=payload)
        self.assertEqual(r.status_code, expected, r.get_data(as_text=True))
        return r.get_json()

    def test_computed_vs_explicit_retention(self):
        # Contrato con retention_pct=0.1
        contract = self._post(
            "/api/contracts",
            {
                "project_id": 20,
                "customer_id": 500,
                "code": "CT-RET",
                "retention_pct": 0.1,
            },
        )
        cid = contract["contract_id"]
        # SOV items R1 (1000) y R2 (1000) para permitir dos EP independientes
        self._post(
            f"/api/contracts/{cid}/sov/import",
            {"items": [
                {"item_code": "R1", "qty": 1, "unit_price": 1000},
                {"item_code": "R2", "qty": 1, "unit_price": 1000},
            ]},
        )
        # EP A con deduccion explicita retention 120 (sobre calculo 100)
        ep_a = self._post(
            "/api/ep",
            {"project_id": 20, "contract_id": cid, "ep_number": "EPA"},
            expected=201,
        )
        epa_id = ep_a["ep_id"]
        self._post(
            f"/api/ep/{epa_id}/lines/bulk",
            {"lines": [{"item_code": "R1", "qty_period": 1, "unit_price": 1000, "amount_period": 1000}]},
        )
        # Deduccion explicit retention 120
        self._post(
            f"/api/ep/{epa_id}/deductions/bulk",
            {"deductions": [{"type": "retention", "description": "manual", "amount": 120}]},
        )
        self._post(f"/api/ep/{epa_id}/approve", {})
        inv_a = self._post(f"/api/ep/{epa_id}/generate-invoice", {})
        # Debe registrar ledger = 120 (no computado 100)
        ledger_a = self.client.get(f"/api/ep/{epa_id}/retention")
        self.assertEqual(ledger_a.status_code, 200)
        data_a = ledger_a.get_json()
        self.assertEqual(data_a.get("retention_held"), 120)

    # EP B sin deduccion explicita -> ledger usa calculado 100 (usa item R2)
        ep_b = self._post(
            "/api/ep",
            {"project_id": 20, "contract_id": cid, "ep_number": "EPB"},
            expected=201,
        )
        epb_id = ep_b["ep_id"]
        self._post(
            f"/api/ep/{epb_id}/lines/bulk",
            {"lines": [{"item_code": "R2", "qty_period": 1, "unit_price": 1000, "amount_period": 1000}]},
        )
        self._post(f"/api/ep/{epb_id}/approve", {})
        inv_b = self._post(f"/api/ep/{epb_id}/generate-invoice", {})
        ledger_b = self.client.get(f"/api/ep/{epb_id}/retention")
        self.assertEqual(ledger_b.status_code, 200)
        data_b = ledger_b.get_json()
        self.assertEqual(data_b.get("retention_held"), 100)

        # Release total EP A
        rel = self._post(f"/api/ep/{epa_id}/retention/release", {})
        self.assertEqual(rel.get("released_amount"), 120)
        ledger_a2 = self.client.get(f"/api/ep/{epa_id}/retention")
        data_a2 = ledger_a2.get_json()
        self.assertEqual(data_a2.get("retention_held"), 0)
        self.assertEqual(data_a2.get("retention_released"), 120)

if __name__ == "__main__":
    unittest.main()
