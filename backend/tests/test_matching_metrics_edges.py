#!/usr/bin/env python3
import os
import sqlite3
import uuid
import time
from datetime import datetime, timedelta, UTC
import unittest

import server  # noqa: F401


class MatchingMetricsEdgeCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        cls.db_path = os.path.join(data_dir, f'test_matching_edges_{uuid.uuid4().hex[:8]}.db')
        os.environ['DB_PATH'] = cls.db_path
        now = datetime.now(UTC)
        old = now - timedelta(days=120)
        with sqlite3.connect(cls.db_path) as con:
            cur = con.cursor()
            cur.executescript(
                """
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
                """
            )
            # Seed diverse data (recent + old)
            recents = [
                (1, '[1,2]', 1, 0.9),
                (2, '[1]', 0, 0.4),
                (3, '[1,2,3]', 1, 0.8),
            ]
            olds = [
                (10, '[1,2]', 1, 0.7),
                (11, '[1]', 0, 0.3),
            ]
            for inv, cand, acc, conf in recents:
                cur.execute("INSERT INTO ap_match_events(invoice_id, source_json, candidates_json, chosen_json, confidence, reasons, accepted, created_at) VALUES(?,?,?,?,?,?,?,?)", (inv, '{}', cand, '{}', conf, '[]', acc, now.isoformat()))
            for inv, cand, acc, conf in olds:
                cur.execute("INSERT INTO ap_match_events(invoice_id, source_json, candidates_json, chosen_json, confidence, reasons, accepted, created_at) VALUES(?,?,?,?,?,?,?,?)", (inv, '{}', cand, '{}', conf, '[]', acc, old.isoformat()))
            # Links (some old)
            cur.executemany("INSERT INTO ap_po_links(invoice_id, amount, created_at) VALUES(?,?,?)", [
                (1, 100, now.isoformat()),
                (1, 40, now.isoformat()),
                (2, 50, now.isoformat()),
                (10, 55, old.isoformat()),
            ])
            # AR events
            cur.execute("INSERT INTO ar_map_events(user_id, payload, created_at) VALUES(?,?,?)", ('u', '{}', now.isoformat()))
            cur.execute("INSERT INTO ar_map_events(user_id, payload, created_at) VALUES(?,?,?)", ('u', '{}', old.isoformat()))
            # Rules
            cur.executemany("INSERT INTO ar_project_rules(kind, pattern, project_id, created_at) VALUES(?,?,?,?)", [
                ('k', 'AAA', 'P1', now.isoformat()),
                ('k', 'BBB', 'P2', now.isoformat()),
                ('k', 'CCC', 'P3', now.isoformat()),
            ])
            # Invoices (some without project, some old)
            cur.executemany("INSERT INTO sales_invoices(id, project_id, created_at) VALUES(?,?,?)", [
                (100, 'P1', now.isoformat()),
                (101, 'P2', now.isoformat()),
                (102, '', now.isoformat()),
                (103, 'P3', now.isoformat()),
                (104, 'P1', old.isoformat()),
                (105, '', old.isoformat()),
            ])
            con.commit()
        cls.app = server.app
        cls.client = cls.app.test_client()

    def test_window_zero_no_filter(self):
        r0 = self.client.get('/api/matching/metrics?window_days=0&top=3')
        self.assertEqual(r0.status_code, 200)
        data_all = r0.get_json()
        self.assertGreaterEqual(data_all['ap']['events_total'], 5)
        # Compare with a 30-day window (should be fewer events than total)
        r30 = self.client.get('/api/matching/metrics?window_days=30&top=3')
        data_30 = r30.get_json()
        self.assertLessEqual(data_30['ap']['events_total'], data_all['ap']['events_total'])

    def test_top_zero_returns_none_or_empty(self):
        r = self.client.get('/api/matching/metrics?window_days=30&top=0')
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        # With top=0 we expect no top_projects (None) or empty list
        self.assertIn('ar', body)
        self.assertTrue(body['top'] == 0)
        self.assertTrue(body['ar'].get('top_projects') in (None, [], []))

    def test_cache_hit(self):
        r1 = self.client.get('/api/matching/metrics?window_days=15&top=2')
        d1 = r1.get_json()
        self.assertFalse(d1.get('cache_hit'))
        time.sleep(0.2)
        r2 = self.client.get('/api/matching/metrics?window_days=15&top=2')
        d2 = r2.get_json()
        self.assertTrue(d2.get('cache_hit'))

    def test_large_window_same_as_zero(self):
        # 365 window should include old entries, same total as window 0 for seeded data
        r_all = self.client.get('/api/matching/metrics?window_days=0&top=3')
        r_365 = self.client.get('/api/matching/metrics?window_days=365&top=3')
        self.assertEqual(r_all.get_json()['ap']['events_total'], r_365.get_json()['ap']['events_total'])


if __name__ == '__main__':
    unittest.main()
