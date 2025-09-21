import unittest

from backend import server
from backend.db_utils import db_conn
from backend.api_ap_match import _table_exists


class ApMatchOverAllocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = server.app
        cls.client = cls.app.test_client()
        cls._prepare_data()

    @classmethod
    def _prepare_data(cls):
        with db_conn() as conn:
            # Ensure purchase_orders_unified exists with one PO total 5000
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
                conn.executescript(
                    """
                    INSERT INTO purchase_orders_unified(
                        id,po_number,po_date,vendor_rut,total_amount,
                        currency,status,source_platform
                    ) VALUES(
                        1,'PO-X','2025-09-10','33333333-3',5000,'CLP','open','manual'
                    );
                    """
                )
            else:
                conn.executescript(
                    """
                    INSERT INTO purchase_orders_unified(
                        id,po_number,po_date,vendor_rut,total_amount,
                        currency,status
                    ) VALUES(
                        1,'PO-X','2025-09-10','33333333-3',5000,'CLP','open'
                    );
                    """
                )
            # Minimal lines table to satisfy potential lookups
            # (not strictly needed for confirm)
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
            conn.execute(
                "INSERT INTO v_po_line_balances_pg("
                "po_line_id,po_id,qty_remaining,amt_remaining) "
                "VALUES(?,?,?,?)",
                ('LX1', 1, 10, 5000),
            )
            conn.commit()

    def test_confirm_over_allocation(self):
        # Exceed total_amount (5000) by allocating 5100
        links = [
            {"po_id": 1, "po_line_id": "LX1", "amount": 3000},
            {"po_id": 1, "po_line_id": "LX1", "amount": 2100},
        ]
        r = self.client.post('/api/ap-match/confirm', json={
            'invoice_id': 77701,
            'links': links,
            'user_id': 'tester'
        })
        self.assertEqual(r.status_code, 422, r.data)
        payload = r.get_json()
        self.assertEqual(payload.get('error'), 'over_allocation')
        violations = payload.get('violations') or []
        self.assertTrue(any(v.get('po_id') == '1' for v in violations))


if __name__ == '__main__':
    unittest.main()
