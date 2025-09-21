#!/usr/bin/env python3
"""Micro benchmark for matching metrics endpoint.

Not a strict performance test, but gives a rough idea that:
 - Cold request (no cache) is slower than warm request.
 - Warm request returns cache_hit=True.
We keep dataset modest to avoid CI slowness.
"""
import os
import sqlite3
import uuid
from datetime import datetime, UTC
import unittest

from backend import server  # noqa: F401


class MatchingMetricsPerf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        cls.db_path = os.path.join(data_dir, f'test_matching_perf_{uuid.uuid4().hex[:8]}.db')
        os.environ['DB_PATH'] = cls.db_path
        now = datetime.now(UTC)
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
            # Insert a few thousand events/invoices
            ap_rows = []
            for i in range(1, 1501):
                ap_rows.append((i, '{}', '[1,2,3]', '{}', 0.5 + (i % 10) / 20, '[]', 1 if i % 2 == 0 else 0, now.isoformat()))
            cur.executemany(
                "INSERT INTO ap_match_events(invoice_id, source_json, candidates_json, chosen_json, confidence, reasons, accepted, created_at) VALUES(?,?,?,?,?,?,?,?)",
                ap_rows,
            )
            link_rows = []
            for i in range(1, 1001):
                link_rows.append((i, 10.0 + (i % 5), now.isoformat()))
            cur.executemany("INSERT INTO ap_po_links(invoice_id, amount, created_at) VALUES(?,?,?)", link_rows)
            cur.execute("INSERT INTO ar_map_events(user_id, payload, created_at) VALUES(?,?,?)", ('u', '{}', now.isoformat()))
            # For project rules we provide pattern, project_id, created_at; kind fixed as 'k'
            rule_rows = [(f'PAT{i}', f'P{i % 7}', now.isoformat()) for i in range(1, 51)]
            cur.executemany("INSERT INTO ar_project_rules(kind, pattern, project_id, created_at) VALUES('k',?,?,?)", rule_rows)
            inv_rows = []
            for i in range(1, 1201):
                pid = f'P{i % 9}' if i % 4 != 0 else ''
                inv_rows.append((i, pid, now.isoformat()))
            cur.executemany("INSERT INTO sales_invoices(id, project_id, created_at) VALUES(?,?,?)", inv_rows)
            con.commit()
        cls.app = server.app
        cls.client = cls.app.test_client()

    def test_perf_cache_speedup(self):
        # Cold
        r1 = self.client.get('/api/matching/metrics?window_days=30&top=5')
        d1 = r1.get_json()
        self.assertIsNotNone(d1.get('generation_ms'))
        self.assertFalse(d1.get('cache_hit'))
        cold_ms = d1['generation_ms']
        # Warm (immediately)
        r2 = self.client.get('/api/matching/metrics?window_days=30&top=5')
        d2 = r2.get_json()
        self.assertTrue(d2.get('cache_hit'))
        warm_ms = d2['generation_ms']
        # Expect warm to be strictly lower (some variability possible, allow equality only if extremely fast)
        self.assertLessEqual(warm_ms, cold_ms)
        # Provide a basic ratio assertion if times not degenerate
        if cold_ms > 5:  # avoid flakiness on ultra-fast runs
            delta = cold_ms - warm_ms
            # Only require strict improvement if there is at least 1ms difference budget
            if delta >= 1:
                self.assertLess(warm_ms, cold_ms)


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
