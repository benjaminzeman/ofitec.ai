#!/usr/bin/env python3
import json
import unittest


class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Import lazily to avoid running the server
        from backend import server

        cls.app = server.app
        cls.client = cls.app.test_client()

    def test_status(self):
        resp = self.client.get('/api/status')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('version', data)
        self.assertIn('puerto_oficial', data)

    def test_providers_contract(self):
        resp = self.client.get('/api/providers')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        if data:
            p = data[0]
            # Minimal contract
            for key in ['id', 'rut', 'name', 'totalAmount']:
                self.assertIn(key, p)

    def test_financial_contract(self):
        resp = self.client.get('/api/financial')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('summary', data)
        self.assertIn('movements', data)
        self.assertIsInstance(data['movements'], list)
        summary = data['summary']
        for key in ['totalRevenue', 'totalExpenses', 'netProfit', 'profitMargin']:
            self.assertIn(key, summary)

    def test_facturas_compra_view(self):
        resp = self.client.get('/api/finanzas/facturas_compra?page=1&page_size=5')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('items', data)
        self.assertIn('meta', data)

    def test_cartola_bancaria_view(self):
        resp = self.client.get('/api/finanzas/cartola_bancaria?page=1&page_size=5')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('items', data)
        self.assertIn('meta', data)

    def test_facturas_venta_view(self):
        resp = self.client.get('/api/finanzas/facturas_venta?page=1&page_size=5')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('items', data)
        self.assertIn('meta', data)


if __name__ == '__main__':
    unittest.main()
