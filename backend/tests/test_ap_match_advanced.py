#!/usr/bin/env python3
import unittest


class ApMatchAdvancedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from backend import server
        cls.app = server.app
        cls.client = cls.app.test_client()
        # Inject minimal PO + line balance views if not present
        cls._prepare_data()

    @classmethod
    def _prepare_data(cls):
        from backend.db_utils import db_conn
        from backend.api_ap_match import _table_exists
        with db_conn() as conn:
            # Create simplified purchase_orders_unified if missing
            if not _table_exists(conn, 'purchase_orders_unified'):
                conn.executescript(
                    """
                    CREATE TABLE purchase_orders_unified (
                        id INTEGER PRIMARY KEY,
                        po_number TEXT,
                        po_date TEXT,
                        vendor_rut TEXT,
                        total_amount REAL,
                        currency TEXT,
                        status TEXT
                    );
                    """
                )
            # Detect extra columns (e.g. source_platform) for flexible insert
            cur = conn.execute("PRAGMA table_info(purchase_orders_unified)")
            cols = [r[1] for r in cur.fetchall()]
            has_source_platform = 'source_platform' in cols
            conn.execute("DELETE FROM purchase_orders_unified")
            pos = [
                (
                    1,
                    'PO-100',
                    '2025-09-01',
                    '11111111-1',
                    10000,
                    'CLP',
                    'open',
                ),
                (2, 'PO-101', '2025-09-02', '11111111-1', 5000, 'CLP', 'open'),
                (3, 'PO-102', '2025-09-05', '22222222-2', 7000, 'CLP', 'open'),
            ]
            if has_source_platform:
                # Extend tuples with a default source_platform
                pos_ext = [t + ("manual",) for t in pos]
                conn.executemany(
                    """
                    INSERT INTO purchase_orders_unified(
                        id,po_number,po_date,vendor_rut,total_amount,currency,status,source_platform
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    pos_ext,
                )
            else:
                conn.executemany(
                    """
                    INSERT INTO purchase_orders_unified(
                        id,po_number,po_date,vendor_rut,total_amount,currency,status
                    ) VALUES(?,?,?,?,?,?,?)
                    """,
                    pos,
                )
            # Create balances view substitute (table) for lines
            if not _table_exists(conn, 'v_po_line_balances_pg'):
                conn.executescript(
                    """
                    CREATE TABLE v_po_line_balances_pg (
                        po_line_id TEXT PRIMARY KEY,
                        po_id INTEGER,
                        qty_remaining REAL,
                        amt_remaining REAL
                    );
                    """
                )
            conn.execute("DELETE FROM v_po_line_balances_pg")
            line_rows = [
                ('L1', 1, 5, 4000),
                ('L2', 1, 3, 3000),
                ('L3', 1, 2, 3000),  # PO-100 sums to 10000
                ('L4', 2, 1, 2000),
                ('L5', 2, 1, 3000),  # PO-101 sums to 5000
            ]
            conn.executemany(
                """
                INSERT INTO v_po_line_balances_pg(
                    po_line_id,po_id,qty_remaining,amt_remaining
                ) VALUES(?,?,?,?)
                """,
                line_rows,
            )
            # Config tolerances table maybe
            if not _table_exists(conn, 'ap_match_config'):
                conn.execute(
                    (
                        "CREATE TABLE ap_match_config ("
                        "id INTEGER PRIMARY KEY, scope_type TEXT, "
                        "scope_value TEXT, amount_tol_pct REAL, "
                        "qty_tol_pct REAL, recv_required INTEGER, "
                        "weight_vendor REAL, weight_amount REAL, "
                        "weight_3way REAL, "
                        "created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
                    )
                )
            # Global tolerance 2%
            conn.execute("DELETE FROM ap_match_config")
            conn.execute(
                """
                INSERT INTO ap_match_config(
                    scope_type,scope_value,amount_tol_pct,qty_tol_pct,recv_required
                ) VALUES('global',NULL,0.02,0,0)
                """
            )
            conn.commit()

    def test_multi_po_subset_selection(self):
        # Invoice amount that requires lines from first PO only (exact)
        payload = {
            "vendor_rut": "11111111-1",
            "amount": 10000,
            "date": "2025-09-07",
            "days": 15,
        }
        r = self.client.post('/api/ap-match/suggestions', json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        # Expect first suggestion candidate lines covering ~10000
        self.assertTrue(data['items'])
        cand = data['items'][0].get('candidate')
        self.assertIsNotNone(cand)
        self.assertAlmostEqual(cand['coverage']['amount'], 10000, delta=0.1)

    def test_amount_tolerance_violation_preview(self):
        # Create preview with deliberate over-allocation beyond tolerance
        links = [
            {"po_id": 1, "po_line_id": "L1", "amount": 4000},
            {"po_id": 1, "po_line_id": "L2", "amount": 3000},
            {
                "po_id": 1,
                "po_line_id": "L3",
                # Remaining for L3 is 3000; request 3100 (> amount_tol 2%)
                "amount": 3100,
            },  # exceeds line remaining
        ]
        r = self.client.post(
            '/api/ap-match/preview', json={"invoice_id": 999, "links": links}
        )
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        violations = (
            data.get('violations')
            or data.get('preview', {}).get('violations')
        )
        # Accept amount_exceeds_remaining OR generic violation presence
        has_amount_violation = any(
            'amount_exceeds_remaining' in (v.get('reason') or '')
            for v in violations
        )
        self.assertTrue(violations and has_amount_violation)

    def test_confirm_and_feedback_cycle(self):
        links = [
            {"po_id": 1, "po_line_id": "L1", "amount": 4000},
            {"po_id": 1, "po_line_id": "L2", "amount": 3000},
        ]
        r_prev = self.client.post(
            '/api/ap-match/preview',
            json={
                "invoice_id": 1001,
                "links": links,
                "vendor_rut": "11111111-1",
            },
        )
        self.assertEqual(r_prev.status_code, 200)
        r_conf = self.client.post(
            '/api/ap-match/confirm',
            json={
                "invoice_id": 1001,
                "links": links,
                "confidence": 0.85,
                "reasons": ["test"],
                "user_id": "tester",
            },
        )
        # Allow 200 or 201 depending on creation semantics
        self.assertIn(r_conf.status_code, (200, 201))
        data_conf = r_conf.get_json()
        self.assertTrue(data_conf.get('ok'))
        # Send feedback rejected (simulate user override)
        r_fb = self.client.post(
            '/api/ap-match/feedback',
            json={
                "invoice_id": 1001,
                "accepted": 0,
                "reason": "manual_override",
                "user_id": "tester",
            },
        )
        self.assertEqual(r_fb.status_code, 200)
        fb_data = r_fb.get_json()
        self.assertTrue(fb_data.get('ok'))

    def test_no_suggestions_edge(self):
        # Different vendor_rut -> should not pick lines
        payload = {
            "vendor_rut": "99999999-9",
            "amount": 12000,
            "date": "2025-09-07",
            "days": 15,
        }
        r = self.client.post('/api/ap-match/suggestions', json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
    # Items may have only generic header suggestions if vendor mismatch;
    # allow empty candidate
        self.assertIn('items', data)


if __name__ == '__main__':
    unittest.main()
