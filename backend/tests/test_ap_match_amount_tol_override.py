import unittest

import server
from db_utils import db_conn
from api_ap_match import _table_exists


class ApMatchAmountTolOverrideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = server.app
        cls.client = cls.app.test_client()
        cls._prepare_data()

    @classmethod
    def _prepare_data(cls):
        with db_conn() as conn:
            # Ensure config with small global tolerance 1%
            if not _table_exists(conn, 'ap_match_config'):
                conn.execute(
                    (
                        "CREATE TABLE ap_match_config ("
                        "id INTEGER PRIMARY KEY, scope_type TEXT, "
                        "scope_value TEXT, amount_tol_pct REAL, "
                        "qty_tol_pct REAL, recv_required INTEGER, "
                        "weight_vendor REAL, weight_amount REAL, "
                        "weight_3way REAL, created_at TEXT "
                        "DEFAULT CURRENT_TIMESTAMP)"
                    )
                )
            conn.execute("DELETE FROM ap_match_config")
            conn.execute(
                "INSERT INTO ap_match_config("  # global row
                "scope_type,scope_value,amount_tol_pct,"
                "qty_tol_pct,recv_required) "
                "VALUES('global',NULL,0.01,0,0)"
            )
            # Minimal PO + lines so suggestions can compute
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
            conn.execute("DELETE FROM purchase_orders_unified")
            cur = conn.execute("PRAGMA table_info(purchase_orders_unified)")
            cols = [r[1] for r in cur.fetchall()]
            has_source_platform = 'source_platform' in cols
            if has_source_platform:
                conn.execute(
                    "INSERT INTO purchase_orders_unified("  # PO row
                    "id,po_number,po_date,vendor_rut,total_amount,"
                    "currency,status,source_platform) VALUES(21,'PO-TOL',"
                    "'2025-09-12','55555555-5',10000,'CLP','open','manual')"
                )
            else:
                conn.execute(
                    "INSERT INTO purchase_orders_unified("  # PO row
                    "id,po_number,po_date,vendor_rut,total_amount,"
                    "currency,status) VALUES(21,'PO-TOL','2025-09-12',"
                    "'55555555-5',10000,'CLP','open')"
                )
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
            # Two lines totalling 10000
            conn.executemany(
                "INSERT INTO v_po_line_balances_pg("
                "po_line_id,po_id,qty_remaining,amt_remaining) "
                "VALUES(?,?,?,?)",
                [
                    ('TL1', 21, 5, 6000),
                    ('TL2', 21, 5, 4000),
                ],
            )
            conn.commit()

    def test_suggestions_strict_global_then_override(self):
        # 10050 is 0.5% over 10000 -> within 1% global tolerance
        payload = {
            'vendor_rut': '55555555-5',
            'amount': 10050,  # 0.5% over
            'date': '2025-09-15',
            'days': 10,
        }
        r = self.client.post('/api/ap-match/suggestions', json=payload)
        self.assertEqual(r.status_code, 200, r.data)
        data = r.get_json()
        self.assertIn('items', data)
        # 10300 is 3% over -> should fail under 1% global unless override
        payload2 = {
            'vendor_rut': '55555555-5',
            'amount': 10300,  # 3% over base
            'date': '2025-09-15',
            'days': 10,
        }
        r2 = self.client.post('/api/ap-match/suggestions', json=payload2)
        self.assertEqual(r2.status_code, 200)
        data2 = r2.get_json()
        # Candidate may be empty or missing due to strict tolerance
        cand2 = data2['items'][0].get('candidate') if data2['items'] else None
        self.assertFalse(cand2)
        # Override tolerance to 5% -> now 3% over should produce candidate
        payload2['amount_tol'] = 0.05
        r3 = self.client.post('/api/ap-match/suggestions', json=payload2)
        self.assertEqual(r3.status_code, 200)
        data3 = r3.get_json()
        cand3 = data3['items'][0].get('candidate') if data3['items'] else None
        self.assertTrue(cand3)
        if cand3:
            self.assertGreaterEqual(cand3['coverage']['amount'], 10000)


if __name__ == '__main__':
    unittest.main()
