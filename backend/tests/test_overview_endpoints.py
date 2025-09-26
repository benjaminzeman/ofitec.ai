#!/usr/bin/env python3
import unittest


class OverviewEndpointsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import server
        cls.app = server.app
        cls.client = cls.app.test_client()

    def test_projects_overview(self):
        resp = self.client.get('/api/projects/overview')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        # Minimal contract
        self.assertIn('portfolio', data)
        self.assertIn('salud', data)
        self.assertIn('wip', data)
        self.assertIn('acciones', data)
        self.assertIsInstance(data['acciones'], list)

    def test_finance_overview(self):
        resp = self.client.get('/api/finance/overview')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        for key in ['cash', 'revenue', 'ar', 'ap', 'acciones']:
            self.assertIn(key, data)
        self.assertIn('today', data['cash'])
        self.assertIn('month', data['revenue'])

    def test_ceo_overview(self):
        resp = self.client.get('/api/ceo/overview')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        for key in ['cash', 'revenue', 'projects', 'risk', 'acciones']:
            self.assertIn(key, data)
        self.assertIn('today', data['cash'])
        self.assertIn('month', data['revenue'])
        self.assertIn('total', data['projects'])


if __name__ == '__main__':
    unittest.main()
