import os
import sqlite3
import tempfile
from datetime import date, timedelta

from server import app  # assumes blueprint already registered


# Helper to set a temporary DB per test module
def _new_db():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    os.environ["DB_PATH"] = tmp.name
    con = sqlite3.connect(tmp.name)
    return con, tmp.name


def _insert_base_rows(con, rows):
    cur = con.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sales_invoices(
            id INTEGER PRIMARY KEY,
            invoice_number TEXT,
            invoice_date TEXT,
            customer_rut TEXT,
            customer_name TEXT,
            total_amount REAL,
            currency TEXT,
            status TEXT,
            source_platform TEXT
        )
        """
    )
    cur.executemany(
        """
        INSERT INTO sales_invoices(
            invoice_number, invoice_date, customer_rut, customer_name,
            total_amount, currency, status, source_platform
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        rows,
    )
    con.commit()


def test_fallback_minimal_columns():
    con, path = _new_db()
    try:
        # Minimal table: only number + date
        cur = con.cursor()
        cur.execute(
            "CREATE TABLE sales_invoices("  # minimal subset
            "id INTEGER PRIMARY KEY,"
            " invoice_number TEXT,"
            " invoice_date TEXT)"
        )
        cur.execute(
            "INSERT INTO sales_invoices(invoice_number, invoice_date) "
            "VALUES(?, ?)",
            ("F-1", "2025-01-10"),
        )
        con.commit()
        client = app.test_client()
        r = client.get("/api/sales_invoices?page=1&page_size=10")
        assert r.status_code == 200
        data = r.get_json()
        assert data["items"][0]["documento_numero"] == "F-1"
        # Fields not present defaulted
        assert data["items"][0]["cliente_rut"] is None
        assert data["items"][0]["monto_total"] == 0
    finally:
        con.close()
        os.remove(path)


def test_filters_and_search():
    con, path = _new_db()
    try:
        today = date.today()
        rows = [
            (
                "A-1",
                str(today - timedelta(days=5)),
                "111-1",
                "Alpha",
                1000,
                "CLP",
                "paid",
                "sys",
            ),
            (
                "A-2",
                str(today - timedelta(days=3)),
                "222-2",
                "Beta",
                2000,
                "USD",
                "open",
                "erp",
            ),
            (
                "A-3",
                str(today - timedelta(days=1)),
                "111-1",
                "AlfaCorp",
                3000,
                "CLP",
                "open",
                "erp",
            ),
        ]
        _insert_base_rows(con, rows)
        client = app.test_client()
        # Filter rut
        r1 = client.get("/api/sales_invoices?rut=111-1")
        assert r1.status_code == 200
        assert len(r1.get_json()["items"]) == 2
        # Filter currency
        r2 = client.get("/api/sales_invoices?moneda=USD")
        assert len(r2.get_json()["items"]) == 1
        # Date range
        date_from = str(today - timedelta(days=4))
        r3 = client.get(f"/api/sales_invoices?date_from={date_from}")
        assert len(r3.get_json()["items"]) == 2
        # Search (should match both Alpha variants by partial)
        r4 = client.get("/api/sales_invoices?search=Al")
        assert len(r4.get_json()["items"]) >= 2
    finally:
        con.close()
        os.remove(path)


def test_ordering():
    con, path = _new_db()
    try:
        today = date.today()
        rows = [
            (
                "O-1",
                str(today - timedelta(days=2)),
                "1",
                "Uno",
                500,
                "CLP",
                "open",
                "sys",
            ),
            (
                "O-2",
                str(today - timedelta(days=1)),
                "2",
                "Dos",
                100,
                "CLP",
                "open",
                "sys",
            ),
            (
                "O-3",
                str(today - timedelta(days=3)),
                "3",
                "Tres",
                900,
                "CLP",
                "open",
                "sys",
            ),
        ]
        _insert_base_rows(con, rows)
        client = app.test_client()
        r_asc = client.get(
            "/api/sales_invoices?order_by=monto_total&order_dir=ASC"
        )
        items_asc = r_asc.get_json()["items"]
        assert [i["monto_total"] for i in items_asc] == sorted(
            i["monto_total"] for i in items_asc
        )
        r_invalid = client.get("/api/sales_invoices?order_by=zzz")
        # Default fecha DESC => first should be the most recent date (O-2)
        assert r_invalid.get_json()["items"][0]["documento_numero"] == "O-2"
    finally:
        con.close()
        os.remove(path)


def test_view_branch_with_project():
    con, path = _new_db()
    try:
        cur = con.cursor()
        # Base view (v_facturas_venta)
        cur.executescript(
            """
            CREATE TABLE raw_sales(
                id INTEGER PRIMARY KEY,
                invoice_number TEXT,
                fecha TEXT,
                cliente_rut TEXT,
                cliente_nombre TEXT,
                documento_numero TEXT,
                monto_total REAL,
                moneda TEXT,
                estado TEXT,
                project_id INTEGER
            );
            INSERT INTO raw_sales(
                invoice_number, fecha, cliente_rut, cliente_nombre,
                documento_numero, monto_total, moneda, estado, project_id
            ) VALUES
                ('V-1','2025-01-05','9-9','Vista','V-1',1500,'CLP','open',10),
                ('V-2','2025-01-06','9-9','Vista','V-2',3000,'CLP','paid',11);
            CREATE VIEW v_facturas_venta AS
                SELECT fecha, cliente_rut, cliente_nombre, documento_numero,
                       monto_total, moneda, estado
                FROM raw_sales;
            CREATE VIEW v_sales_invoices_with_project AS
                SELECT fecha, cliente_rut, cliente_nombre, documento_numero,
                       monto_total, moneda, estado, project_id
                FROM raw_sales;
            """
        )
        con.commit()
        client = app.test_client()
        # Without project filter -> 2
        r_all = client.get("/api/sales_invoices")
        assert len(r_all.get_json()["items"]) == 2
        # With project filter uses enriched view
        r_proj = client.get("/api/sales_invoices?project_id=10")
        items_proj = r_proj.get_json()["items"]
        assert len(items_proj) == 1
        assert items_proj[0]["documento_numero"] == "V-1"
    finally:
        con.close()
        os.remove(path)
