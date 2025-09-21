#!/usr/bin/env python3
import os
import sqlite3
import uuid
import unittest
from datetime import datetime, UTC

from backend import server  # noqa: F401
from backend.api_matching_metrics import _CACHE  # access internal for test TTL manipulation


class MatchingMetricsCacheTTLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        cls.db_path = os.path.join(data_dir, f'test_matching_cachettl_{uuid.uuid4().hex[:8]}.db')
        os.environ['DB_PATH'] = cls.db_path
        now = datetime.now(UTC)
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
                CREATE TABLE sales_invoices(
                  id INTEGER PRIMARY KEY,
                  project_id TEXT,
                  created_at TEXT
                );
                INSERT INTO ap_match_events(invoice_id, source_json, candidates_json, chosen_json, confidence, reasons, accepted, created_at)
                  VALUES(1,'{{}}','[1]','{{}}',0.8,'[]',1,'{now.isoformat()}');
                INSERT INTO sales_invoices(id, project_id, created_at)
                  VALUES(1,'P1','{now.isoformat()}');
                """
            )
        cls.app = server.app
        cls.client = cls.app.test_client()

    def test_cache_ttl_expiry(self):
        # First call -> cold
        r1 = self.client.get('/api/matching/metrics?window_days=0&top=1')
        d1 = r1.get_json()
        self.assertFalse(d1.get('cache_hit'))
        # Second call immediately -> warm
        r2 = self.client.get('/api/matching/metrics?window_days=0&top=1')
        d2 = r2.get_json()
        self.assertTrue(d2.get('cache_hit'))
        # Simulate TTL expiry by rewinding stored timestamp
        key = (0, 1)
        if key in _CACHE:
            ts, payload = _CACHE[key]
            # Force it to look old ( > 30s )
            _CACHE[key] = (ts - 120.0, payload)
        # Third call should rebuild (cache_hit absent/False)
        r3 = self.client.get('/api/matching/metrics?window_days=0&top=1')
        d3 = r3.get_json()
        self.assertFalse(d3.get('cache_hit'))


if __name__ == '__main__':
    unittest.main()
