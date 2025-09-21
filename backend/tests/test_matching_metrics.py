#!/usr/bin/env python3
import os
import sqlite3
import unittest
import uuid

from backend import server  # ensure app import (registers blueprint)


class MatchingMetricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use an isolated temporary DB file per test class
        # Place test DB under root data/ directory (../.. from tests)
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        test_db = os.path.join(data_dir, f'test_matching_metrics_{uuid.uuid4().hex[:8]}.db')
        os.environ['DB_PATH'] = test_db
        # Initialize some minimal tables / seed data
        with sqlite3.connect(test_db) as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS ap_match_events(
                  id INTEGER PRIMARY KEY,
                  invoice_id INTEGER NOT NULL,
                  source_json TEXT NOT NULL,
                  candidates_json TEXT NOT NULL,
                  chosen_json TEXT,
                  confidence REAL,
                  reasons TEXT,
                  accepted INTEGER,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                  user_id TEXT
                );
                CREATE TABLE IF NOT EXISTS ap_po_links(
                  id INTEGER PRIMARY KEY,
                  invoice_id INTEGER NOT NULL,
                  amount REAL NOT NULL,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ar_map_events(
                  id INTEGER PRIMARY KEY,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                  user_id TEXT,
                  payload TEXT
                );
                CREATE TABLE IF NOT EXISTS ar_project_rules(
                  id INTEGER PRIMARY KEY,
                  kind TEXT,
                  pattern TEXT NOT NULL,
                  project_id TEXT NOT NULL,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS sales_invoices(
                  id INTEGER PRIMARY KEY,
                  project_id TEXT,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                INSERT INTO ap_match_events(invoice_id, source_json, candidates_json, chosen_json, confidence, reasons, accepted)
                    VALUES(1,'{}','[]','{}',0.9,'["rule"]',1),
                          (2,'{}','[]',NULL,0.5,'[]',0);
                INSERT INTO ap_po_links(invoice_id, amount) VALUES(1, 100),(1,50),(2, 75);
                INSERT INTO ar_map_events(user_id, payload) VALUES('u','{}');
                INSERT INTO ar_project_rules(kind, pattern, project_id) VALUES('customer_name_like','CLIENTE','P1');
                INSERT INTO sales_invoices(id, project_id) VALUES(10,'P1'),(11,''),(12,'P1');
                """
            )
        cls.app = server.app
        cls.client = cls.app.test_client()

    def test_matching_metrics_endpoint(self):
        resp = self.client.get('/api/matching/metrics')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('generated_at', data)
        self.assertIn('ap', data)
        self.assertIn('ar', data)
        ap = data['ap']
        ar = data['ar']
        # AP assertions
        self.assertEqual(ap['events_total'], 2)
        self.assertEqual(ap['accepted_total'], 1)
        self.assertAlmostEqual(ap['acceptance_rate'], 0.5, places=4)
        self.assertEqual(ap['total_links'], 3)
        self.assertEqual(ap['distinct_invoices_linked'], 2)
        self.assertAlmostEqual(ap['avg_links_per_invoice'], 1.5, places=2)
        # AR assertions
        self.assertEqual(ar['events_total'], 1)
        self.assertEqual(ar['rules_total'], 1)
        self.assertEqual(ar['invoices_total'], 3)
        self.assertEqual(ar['invoices_with_project'], 2)
        self.assertAlmostEqual(ar['project_assign_rate'], 2/3, places=4)


if __name__ == '__main__':
    unittest.main()
