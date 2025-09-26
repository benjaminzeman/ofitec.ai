#!/usr/bin/env python3
import unittest

class ControlFinancieroApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import server
        cls.app = server.app
        cls.client = cls.app.test_client()

    def test_projects_control_endpoint(self):
        resp = self.client.get('/api/projects/control?with_meta=1')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        # with_meta requested => expect meta
        self.assertIn('projects', data)
        self.assertIsInstance(data['projects'], list)
        self.assertIn('meta', data)
        # If there are projects, assert minimal contract keys
        if data['projects']:
            p = data['projects'][0]
            for k in ['project_name', 'budget_cost', 'committed', 'available_conservative']:
                self.assertIn(k, p)

    def test_aliases_project_endpoint(self):
        payload = {"from": "Proyecto X Excel", "to": "Proyecto X ERP"}
        resp = self.client.post('/api/aliases/project', json=payload)
        self.assertIn(resp.status_code, (200, 201))
        data = resp.get_json()
        self.assertTrue(data.get('ok', False))

if __name__ == '__main__':
    unittest.main()
