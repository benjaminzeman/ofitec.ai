#!/usr/bin/env python3
import unittest

class EpStagingViolationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import server  # ensure blueprints
        cls.app = server.app
        cls.client = cls.app.test_client()

    def _post(self, path, payload, expected=200):
        r = self.client.post(path, json=payload)
        self.assertEqual(r.status_code, expected, r.get_data(as_text=True))
        return r.get_json()

    def test_staging_violation_blocks_promote(self):
        # 1. Crear contrato + SOV con item código IT1 monto 1000
        contract = self._post(
            "/api/contracts",
            {"project_id": 10, "customer_id": 77, "code": "CT-STAGE"},
        )
        cid = contract["contract_id"]
        self._post(
            f"/api/contracts/{cid}/sov/import",
            {"items": [{"item_code": "IT1", "qty": 1, "unit_price": 1000}]},
        )
        # 2. Crear staging con fila que excede cap (intentamos 1200)
        rows = [
            {"Codigo": "IT1", "Cantidad": 1, "Precio Unitario": 1200, "Capitulo": "A"}
        ]
        stg = self._post(
            "/api/ep/import/staging",
            {
                "project_id": 10,
                "contract_id": cid,
                "rows": rows,
            },
            expected=201,
        )
        sid = stg["staging_id"]
        # 3. Validar => debe registrar violacion ep_exceeds_contract_item
        vres = self._post(
            f"/api/ep/import/staging/{sid}/validate",
            {},
        )
        violations = vres.get("violations") or []
        self.assertTrue(violations, "Debe haber violaciones")
        self.assertTrue(
            any(v.get("error") == "ep_exceeds_contract_item" for v in violations)
        )
        # 4. Promover debe fallar con violations_present
        r = self.client.post(
            f"/api/ep/import/staging/{sid}/promote", json={}
        )
        self.assertEqual(r.status_code, 422)
        data = r.get_json()
        self.assertEqual(data.get("error"), "violations_present")

if __name__ == "__main__":
    unittest.main()
