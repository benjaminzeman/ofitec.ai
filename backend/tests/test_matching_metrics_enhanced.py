#!/usr/bin/env python3
import os
import sqlite3
import unittest
import uuid
from datetime import datetime, timedelta, UTC

import server  # noqa: F401


class MatchingMetricsEnhancedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        cls.db_path = os.path.join(data_dir, f'test_matching_metrics_enh_{uuid.uuid4().hex[:8]}.db')
        os.environ['DB_PATH'] = cls.db_path
        now = datetime.now(UTC)
        old = now - timedelta(days=40)
        with sqlite3.connect(cls.db_path) as con:
            con.executescript(
                f"""
                CREATE TABLE ap_match_events(
                  id INTEGER PRIMARY KEY,
                  invoice_id INTEGER NOT NULL,
                  source_json TEXT NOT NULL,
                  candidates_json TEXT NOT NULL,
                  chosen_json TEXT,
                  confidence REAL,
                  reasons TEXT,
                  accepted INTEGER,
                  created_at TEXT,
                  user_id TEXT
                );
                CREATE TABLE ap_po_links(
                  id INTEGER PRIMARY KEY,
                  invoice_id INTEGER NOT NULL,
                  amount REAL NOT NULL,
                  created_at TEXT
                );
                CREATE TABLE ar_map_events(
                  id INTEGER PRIMARY KEY,
                  created_at TEXT,
                  user_id TEXT,
                  payload TEXT
                );
                CREATE TABLE ar_project_rules(
                  id INTEGER PRIMARY KEY,
                  kind TEXT,
                  pattern TEXT NOT NULL,
                  project_id TEXT NOT NULL,
                  created_at TEXT
                );
                CREATE TABLE sales_invoices(
                  id INTEGER PRIMARY KEY,
                  project_id TEXT,
                  created_at TEXT
                );
                INSERT INTO ap_match_events(invoice_id, source_json, candidates_json, chosen_json, confidence, reasons, accepted, created_at)
                  VALUES(1,'{{}}','[1,2]','{{}}',0.9,'[]',1,'{now.isoformat()}'),
                        (2,'{{}}','[1]','{{}}',0.4,'[]',0,'{now.isoformat()}'),
                        (3,'{{}}','[1,2,3]','{{}}',0.7,'[]',1,'{old.isoformat()}');
                INSERT INTO ap_po_links(invoice_id, amount, created_at) VALUES
                  (1,100,'{now.isoformat()}'),(1,50,'{now.isoformat()}'),(2,30,'{now.isoformat()}'),(3,20,'{old.isoformat()}');
                INSERT INTO ar_map_events(user_id, payload, created_at) VALUES('u','{{}}','{now.isoformat()}'),('u','{{}}','{old.isoformat()}');
                INSERT INTO ar_project_rules(kind, pattern, project_id, created_at) VALUES
                  ('k','A','P1','{now.isoformat()}'),('k','B','P2','{now.isoformat()}'),('k','C','P1','{old.isoformat()}');
                INSERT INTO sales_invoices(id, project_id, created_at) VALUES
                  (10,'P1','{now.isoformat()}'),(11,'','{now.isoformat()}'),(12,'P2','{now.isoformat()}'),
                  (13,'P1','{old.isoformat()}'),(14,'P3','{old.isoformat()}');
                """
            )
        cls.app = server.app
        cls.client = cls.app.test_client()

    def test_enhanced_metrics_window_and_top(self):
        # window_days=30 should exclude the 'old' records
        r = self.client.get('/api/matching/metrics?window_days=30&top=2')
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data['window_days'], 30)
        self.assertIn('generation_ms', data)
        ap = data['ap']
        ar = data['ar']
        # AP: only two recent events (id 1,2)
        self.assertEqual(ap['events_total'], 2)
        self.assertEqual(ap['accepted_total'], 1)
        self.assertAlmostEqual(ap['acceptance_rate'], 0.5, places=4)
        self.assertIsNotNone(ap['candidates_avg'])
        self.assertIsNotNone(ap['confidence_p50'])
        # AR: only invoices with recent created_at
        self.assertGreaterEqual(ar['invoices_total'], 3)  # 10,11,12
        self.assertIn('top_projects', ar)
        self.assertTrue(ar['top_projects'])
        # cache test
        r2 = self.client.get('/api/matching/metrics?window_days=30&top=2')
        data2 = r2.get_json()
        self.assertTrue(data2.get('cache_hit'))

    def test_projects_breakdown_endpoint(self):
        r = self.client.get('/api/matching/metrics/projects?window_days=0')
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assertIn('items', body)
        if body['items']:
            self.assertIn('project_id', body['items'][0])
            self.assertIn('share', body['items'][0])


if __name__ == '__main__':
    unittest.main()
