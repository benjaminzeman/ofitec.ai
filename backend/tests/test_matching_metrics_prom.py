#!/usr/bin/env python3
import os
import sqlite3
import uuid
import unittest
from datetime import datetime, UTC

from backend import server  # noqa: F401


class MatchingMetricsPromTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        cls.db_path = os.path.join(data_dir, f'test_matching_prom_{uuid.uuid4().hex[:8]}.db')
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
                  VALUES(1,'{{}}','[1,2]','{{}}',0.9,'[]',1,'{now.isoformat()}');
                INSERT INTO ap_po_links(invoice_id, amount, created_at) VALUES(1,100,'{now.isoformat()}');
                INSERT INTO ar_map_events(user_id, payload, created_at) VALUES('u','{{}}','{now.isoformat()}');
                INSERT INTO ar_project_rules(kind, pattern, project_id, created_at) VALUES('k','A','P1','{now.isoformat()}');
                INSERT INTO sales_invoices(id, project_id, created_at) VALUES(10,'P1','{now.isoformat()}');
                """
            )
        cls.app = server.app
        cls.client = cls.app.test_client()

    def test_prometheus_exposition_contains_core_metrics(self):
        rs = self.client.get('/api/matching/metrics?window_days=0&top=1')
        self.assertEqual(rs.status_code, 200)
        prom = self.client.get('/api/matching/metrics/prom?window_days=0&top=1')
        self.assertEqual(prom.status_code, 200)
        text = prom.get_data(as_text=True)
        needles = [
            'matching_ap_events_total',
            'matching_ar_rules_total',
            'matching_ap_acceptance_rate',
            'matching_ar_invoices_total',
            'matching_ar_top_project_count',
            'matching_ap_confidence_bucket',
            'matching_ap_confidence_hist_bucket',
            'matching_ap_confidence_count',
            'matching_ap_confidence_sum',
        ]
        for needle in needles:
            self.assertIn(needle, text)

    def test_prometheus_contains_p95_bucket_gauge(self):
        prom = self.client.get('/api/matching/metrics/prom?window_days=0&top=1')
        self.assertEqual(prom.status_code, 200)
        text = prom.get_data(as_text=True)
        self.assertIn('matching_ap_confidence_p95_bucket', text)
        # raw p95 & p99 gauges (advanced stats)
        self.assertIn('matching_ap_confidence_p95', text)
        # p99 raw (may equal p95 if few events)
        self.assertIn('matching_ap_confidence_p99', text)
        val = None
        for line in text.splitlines():
            if line.startswith('matching_ap_confidence_p95_bucket'):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        val = float(parts[-1])
                    except Exception:  # noqa: BLE001
                        val = None
                break
        self.assertIsNotNone(val)
        if val is not None:
            self.assertTrue(0.0 <= val <= 1.0)
        # bucket p99 gauge presence (could match p95 with sparse data)
        self.assertIn('matching_ap_confidence_p99_bucket', text)

    def test_prometheus_advanced_toggle_off_hides_advanced_metrics(self):
        os.environ['MATCHING_AP_ADVANCED'] = '0'
        try:
            prom = self.client.get('/api/matching/metrics/prom?window_days=0&top=1')
            self.assertEqual(prom.status_code, 200)
            text = prom.get_data(as_text=True)
            self.assertNotIn('matching_ap_confidence_bucket', text)
            self.assertNotIn('matching_ap_confidence_hist_bucket', text)
            self.assertNotIn('matching_ap_confidence_p95_bucket', text)
            self.assertNotIn('matching_ap_confidence_p99_bucket', text)
            self.assertNotIn('matching_ap_confidence_p95', text)
            self.assertNotIn('matching_ap_confidence_p99', text)
        finally:
            os.environ.pop('MATCHING_AP_ADVANCED', None)


if __name__ == '__main__':
    unittest.main()
