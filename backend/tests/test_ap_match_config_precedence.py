import unittest

from backend import server
from backend.db_utils import db_conn
from backend.api_ap_match import _table_exists


class ApMatchConfigPrecedenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = server.app
        cls.client = cls.app.test_client()
        cls._prepare_data()

    @classmethod
    def _prepare_data(cls):
        with db_conn() as conn:
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
            # Global 2%
            conn.execute(
                "INSERT INTO ap_match_config("  # global
                "scope_type,scope_value,amount_tol_pct,qty_tol_pct,"
                "recv_required,weight_vendor,weight_amount,weight_3way) "
                "VALUES('global',NULL,0.02,0,0,0.5,0.3,0.2)"
            )
            # Project override 3%
            conn.execute(
                "INSERT INTO ap_match_config("  # project
                "scope_type,scope_value,amount_tol_pct,qty_tol_pct,"
                "recv_required,weight_vendor,weight_amount,weight_3way) "
                "VALUES('project','P123',0.03,0,0,0.6,0.25,0.15)"
            )
            # Vendor override 5% + recv_required=1
            conn.execute(
                "INSERT INTO ap_match_config("  # vendor
                "scope_type,scope_value,amount_tol_pct,qty_tol_pct,"
                "recv_required,weight_vendor,weight_amount,weight_3way) "
                "VALUES('vendor','99999999-9',0.05,0,1,0.7,0.2,0.1)"
            )
            conn.commit()

    def test_precedence_vendor_project_global(self):
        r = self.client.get(
            '/api/ap-match/config?vendor_rut=99999999-9&project_id=P123'
        )
        self.assertEqual(r.status_code, 200, r.data)
        data = r.get_json()
        eff = data['effective']
        self.assertAlmostEqual(eff['amount_tol_pct'], 0.05, places=4)
        self.assertEqual(eff['recv_required'], 1)
        # Source layers should show defaults, global, project, vendor order
        self.assertEqual(
            data['effective']['source_layers'],
            ['defaults', 'global', 'project', 'vendor']
        )
        weights = data['weights']
        # Vendor weights should apply
        self.assertAlmostEqual(weights['vendor'], 0.7)
        self.assertAlmostEqual(weights['amount'], 0.2)
        self.assertAlmostEqual(weights['three_way'], 0.1)

    def test_project_only(self):
        r = self.client.get('/api/ap-match/config?project_id=P123')
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        eff = data['effective']
        self.assertAlmostEqual(eff['amount_tol_pct'], 0.03, places=4)
        self.assertEqual(eff['recv_required'], 0)
        self.assertEqual(
            eff['source_layers'], ['defaults', 'global', 'project']
        )

    def test_global_only(self):
        r = self.client.get('/api/ap-match/config')
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        eff = data['effective']
        self.assertAlmostEqual(eff['amount_tol_pct'], 0.02, places=4)
        self.assertEqual(eff['source_layers'], ['defaults', 'global'])


if __name__ == '__main__':
    unittest.main()
