import unittest

from backend import server
from backend.db_utils import db_conn
from backend.api_ap_match import _table_exists


class ApMatchInvoiceAggregationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = server.app
        cls.client = cls.app.test_client()
        cls._prepare_data()

    @classmethod
    def _prepare_data(cls):
        with db_conn() as conn:
            # Purchase orders
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
                conn.executemany(
                    """
                    INSERT INTO purchase_orders_unified(
                        id, po_number, po_date, vendor_rut, total_amount,
                        currency, status, source_platform
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    [
                        (
                            10, 'PO-A', '2025-09-01', '44444444-4', 8000,
                            'CLP', 'open', 'manual'
                        ),
                        (
                            11, 'PO-B', '2025-09-02', '44444444-4', 6000,
                            'CLP', 'open', 'manual'
                        ),
                    ],
                )
            else:
                conn.executemany(
                    """
                    INSERT INTO purchase_orders_unified(
                        id, po_number, po_date, vendor_rut, total_amount,
                        currency, status
                    ) VALUES(?,?,?,?,?,?,?)
                    """,
                    [
                        (
                            10, 'PO-A', '2025-09-01', '44444444-4', 8000,
                            'CLP', 'open'
                        ),
                        (
                            11, 'PO-B', '2025-09-02', '44444444-4', 6000,
                            'CLP', 'open'
                        ),
                    ],
                )
            # Lines table
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
            conn.executemany(
                "INSERT INTO v_po_line_balances_pg("
                "po_line_id,po_id,qty_remaining,amt_remaining) "
                "VALUES(?,?,?,?)",
                [
                    ('AL1', 10, 5, 4000),
                    ('AL2', 10, 5, 4000),
                    ('BL1', 11, 3, 3000),
                    ('BL2', 11, 3, 3000),
                ],
            )
            # Ensure ap_po_links modern schema
            if not _table_exists(conn, 'ap_po_links'):
                conn.executescript(
                    """
                    CREATE TABLE ap_po_links (
                        id INTEGER PRIMARY KEY,
                        invoice_id INTEGER,
                        invoice_line_id TEXT,
                        po_id INTEGER,
                        po_line_id TEXT,
                        amount REAL,
                        qty REAL,
                        created_by TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
            conn.execute("DELETE FROM ap_po_links")
            # Insert links for invoice 555 with two POs
            conn.executemany(
                """
                INSERT INTO ap_po_links(
                    invoice_id, invoice_line_id, po_id, po_line_id,
                    amount, qty, created_by
                ) VALUES(?,?,?,?,?,?,?)
                """,
                [
                    (555, 'i1', 10, 'AL1', 3500, 1, 'tester'),
                    (555, 'i2', 10, 'AL2', 3800, 1, 'tester'),
                    (555, 'i3', 11, 'BL1', 2900, 1, 'tester'),
                ],
            )
            conn.commit()

    def test_invoice_aggregation_totals(self):
        r = self.client.get('/api/ap-match/invoice/555')
        self.assertEqual(r.status_code, 200, r.data)
        data = r.get_json()
        self.assertEqual(data['invoice_id'], 555)
        self.assertEqual(len(data['links']), 3)
        totals = data['totals']
        # Expect two PO entries
        self.assertIn('10', totals)
        self.assertIn('11', totals)
        self.assertAlmostEqual(totals['10']['amount_sum'], 7300, places=2)
        self.assertAlmostEqual(totals['11']['amount_sum'], 2900, places=2)


if __name__ == '__main__':
    unittest.main()
