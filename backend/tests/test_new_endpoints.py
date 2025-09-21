#!/usr/bin/env python3
import unittest


class NewApiEndpointsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from backend import server

        cls.app = server.app
        cls.client = cls.app.test_client()

    def test_sales_invoices_list(self):
        resp = self.client.get('/api/sales_invoices?page=1&page_size=5')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('items', data)
        self.assertIn('meta', data)

    def test_ar_map_suggestions(self):
        payload = {"invoice": {"customer_name": "Cliente Demo"}}
        resp = self.client.post('/api/ar-map/suggestions', json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('items', data)
        self.assertIsInstance(data['items'], list)

    def test_ar_map_confirm_validation(self):
        # Missing rules should 422
        resp = self.client.post('/api/ar-map/confirm', json={"rules": []})
        self.assertEqual(resp.status_code, 422)

    def test_treasury_forecast(self):
        resp = self.client.get('/api/finance/treasury/forecast')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('items', data)

    def test_threeway_violations(self):
        resp = self.client.get('/api/threeway/violations')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('items', data)

    def test_ap_match_endpoints(self):
        # Suggestions should work with empty DB returning items or empty list
        payload = {"invoice": {"vendor_rut": "12345678-9", "amount": 1000}}
        r1 = self.client.post('/api/ap-match/suggestions', json=payload)
        self.assertEqual(r1.status_code, 200)
        data1 = r1.get_json()
        self.assertIn('items', data1)

        # Preview requires links otherwise 422
        r2 = self.client.post('/api/ap-match/preview', json={"links": []})
        self.assertEqual(r2.status_code, 422)

        # Confirm requires links otherwise 422
        r3 = self.client.post('/api/ap-match/confirm', json={"links": []})
        self.assertEqual(r3.status_code, 422)

    def test_conciliacion_preview_and_confirm(self):
        # Preview without links -> 422
        r0 = self.client.post('/api/conciliacion/preview', json={"links": []})
        self.assertEqual(r0.status_code, 422)

        # Preview with links -> 200 and structure present
        links = [
            {"bank_movement_id": 1, "sales_invoice_id": 2, "amount": 1000},
            {"bank_movement_id": 1, "purchase_invoice_id": 3, "amount": -500},
        ]
        r1 = self.client.post(
            '/api/conciliacion/preview', json={"links": links}
        )
        self.assertEqual(r1.status_code, 200)
        data = r1.get_json()
        self.assertTrue(data.get('ok'))
        self.assertIn('preview', data)
        self.assertIn('invoice_deltas', data['preview'])
        self.assertIn('movement_deltas', data['preview'])

        # Confirm with links -> 200 ok
        payload = {
            "context": "bank",
            "confidence": 0.8,
            "links": links,
            "metadata": {"user_id": "tester"},
        }
        r2 = self.client.post(
            '/api/conciliacion/confirmar', json=payload
        )
        self.assertEqual(r2.status_code, 200)
        data2 = r2.get_json()
        self.assertTrue(data2.get('ok'))
        self.assertIn('reconciliation_id', data2)

    def test_sync_chipax_endpoint(self):
        r = self.client.post(
            '/api/reconciliaciones/sync_chipax'
        )
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn('ok', data)
        self.assertIn('metrics', data)

    def test_conciliacion_historial(self):
        r = self.client.get('/api/conciliacion/historial')
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn('items', data)


if __name__ == '__main__':
    unittest.main()
