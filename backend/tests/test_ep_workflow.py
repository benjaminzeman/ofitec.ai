#!/usr/bin/env python3
import unittest


class EpWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import server
        cls.app = server.app
        cls.client = cls.app.test_client()

    def _post(self, url, payload, expected=200):
        r = self.client.post(url, json=payload)
        self.assertEqual(
            r.status_code,
            expected,
            f"POST {url} -> {r.status_code} {r.get_data(as_text=True)}",
        )
        return r.get_json()

    def _get(self, url, expected=200):
        r = self.client.get(url)
        self.assertEqual(
            r.status_code,
            expected,
            f"GET {url} -> {r.status_code} {r.get_data(as_text=True)}",
        )
        return r.get_json()

    def test_full_ep_flow_minimal(self):
        # 1. Crear contrato con retención
        contract = self._post(
            "/api/contracts",
            {
                "project_id": 1,
                "customer_id": 1,
                "code": "CT-EP-T1",
                "retention_pct": 0.05,
            },
        )
        cid = contract["contract_id"]

        # 2. Importar SOV mínima
        sov = self._post(
            f"/api/contracts/{cid}/sov/import",
            {
                "items": [
                    {"item_code": "IT1", "qty": 10, "unit_price": 1000},
                    {"item_code": "IT2", "qty": 5, "unit_price": 2000},
                ]
            },
        )
        self.assertGreaterEqual(sov["inserted"], 2)

        # 3. Crear EP header draft
        ep_header = self._post(
            "/api/ep",
            {
                "project_id": 1,
                "contract_id": cid,
                "ep_number": "EP-1",
                "retention_pct": 0.05,
            },
            expected=201,
        )
        ep_id = ep_header["ep_id"]

        # 4. Setear líneas con montos dentro de SOV
        lines = self._post(
            f"/api/ep/{ep_id}/lines/bulk",
            {
                "lines": [
                    {
                        "item_code": "IT1",
                        "qty_period": 2,
                        "unit_price": 1000,
                        "amount_period": 2000,
                    },
                    {
                        "item_code": "IT2",
                        "qty_period": 1,
                        "unit_price": 2000,
                        "amount_period": 2000,
                    },
                ]
            },
        )
        self.assertEqual(lines["count"], 2)

        # 5. Summary antes de aprobar
        summary = self._get(f"/api/ep/{ep_id}/summary")
        self.assertAlmostEqual(summary["lines_subtotal"], 4000)
        self.assertIn("retention_computed", summary)
        self.assertAlmostEqual(summary["retention_computed"], 200.0)

        # 6. Aprobar EP
        approved = self._post(f"/api/ep/{ep_id}/approve", {}, expected=200)
        self.assertEqual(approved["status"], "approved")

        # 7. Generar factura
        invoice = self._post(f"/api/ep/{ep_id}/generate-invoice", {})
        self.assertIn("invoice_id", invoice)
        self.assertGreater(invoice["amount_total"], 0)
        self.assertIn("retention_recorded", invoice)

        # 8. Registrar cobro parcial
        inv_id = invoice["invoice_id"]
        collect = self._post(
            f"/api/ar/invoices/{inv_id}/collect",
            {"amount": invoice["amount_total"] / 2},
        )
        self.assertTrue(collect["ok"])

        # 9. Retención summary
        ret = self._get(f"/api/ep/{ep_id}/retention")
        self.assertGreater(ret["retention_held"], 0)
        self.assertEqual(ret["retention_released"], 0)

        # 10. Liberar retención total
        release = self._post(f"/api/ep/{ep_id}/retention/release", {})
        self.assertTrue(release["ok"])
        ret2 = self._get(f"/api/ep/{ep_id}/retention")
        self.assertEqual(ret2["retention_held"], 0)
        self.assertGreater(ret2["retention_released"], 0)

    def test_duplicate_invoice_guard(self):
        # Crear flujo rápido mínimo
        contract = self._post(
            "/api/contracts",
            {"project_id": 1, "customer_id": 1, "code": "CT-EP-T2"},
        )
        cid = contract["contract_id"]
        self._post(
            f"/api/contracts/{cid}/sov/import",
            {"items": [{"item_code": "ITX", "qty": 1, "unit_price": 1000}]},
        )
        ep_header = self._post(
            "/api/ep",
            {"project_id": 1, "contract_id": cid, "ep_number": "EP-X"},
            expected=201,
        )
        ep_id = ep_header["ep_id"]
        self._post(
            f"/api/ep/{ep_id}/lines/bulk",
            {
                "lines": [
                    {
                        "item_code": "ITX",
                        "qty_period": 1,
                        "unit_price": 1000,
                        "amount_period": 1000,
                    }
                ]
            },
        )
        self._post(f"/api/ep/{ep_id}/approve", {})
        self._post(f"/api/ep/{ep_id}/generate-invoice", {})
        # Segundo intento debe 422 duplicate_invoice
        r = self.client.post(f"/api/ep/{ep_id}/generate-invoice", json={})
        self.assertEqual(r.status_code, 422)
        payload = r.get_json()
        self.assertEqual(payload.get("error"), "duplicate_invoice")

    def test_over_collected_guard(self):
        # Flujo mínimo y cobro excedido
        contract = self._post(
            "/api/contracts",
            {"project_id": 2, "customer_id": 2, "code": "CT-EP-T3"},
        )
        cid = contract["contract_id"]
        self._post(
            f"/api/contracts/{cid}/sov/import",
            {"items": [{"item_code": "ITY", "qty": 1, "unit_price": 500}]},
        )
        ep_header = self._post(
            "/api/ep",
            {"project_id": 2, "contract_id": cid, "ep_number": "EP-Y"},
            expected=201,
        )
        ep_id = ep_header["ep_id"]
        self._post(
            f"/api/ep/{ep_id}/lines/bulk",
            {
                "lines": [
                    {
                        "item_code": "ITY",
                        "qty_period": 1,
                        "unit_price": 500,
                        "amount_period": 500,
                    }
                ]
            },
        )
        self._post(f"/api/ep/{ep_id}/approve", {})
        invoice = self._post(f"/api/ep/{ep_id}/generate-invoice", {})
        inv_total = invoice["amount_total"]
        # Cobrar total
        self._post(
            f"/api/ar/invoices/{invoice['invoice_id']}/collect",
            {"amount": inv_total},
        )
        # Intento extra -> 422 over_collected
        r = self.client.post(
            f"/api/ar/invoices/{invoice['invoice_id']}/collect",
            json={"amount": 1},
        )
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.get_json().get("error"), "over_collected")

    def test_contract_cap_violation(self):
        # Exceder SOV en líneas
        contract = self._post(
            "/api/contracts",
            {"project_id": 3, "customer_id": 3, "code": "CT-EP-T4"},
        )
        cid = contract["contract_id"]
        self._post(
            f"/api/contracts/{cid}/sov/import",
            {"items": [{"item_code": "ITZ", "qty": 1, "unit_price": 100}]},
        )
        ep_header = self._post(
            "/api/ep",
            {"project_id": 3, "contract_id": cid, "ep_number": "EP-Z"},
            expected=201,
        )
        ep_id = ep_header["ep_id"]
        # Intentar línea excedida
        r = self.client.post(
            f"/api/ep/{ep_id}/lines/bulk",
            json={
                "lines": [
                    {
                        "item_code": "ITZ",
                        "qty_period": 2,
                        "unit_price": 100,
                        "amount_period": 200,
                    }
                ]
            },
        )
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.get_json().get("error"), "ep_exceeds_contract_item")


if __name__ == "__main__":
    unittest.main()
