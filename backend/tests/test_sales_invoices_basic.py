from backend import server
import sqlite3
import os
import pytest


@pytest.fixture(name="sales_client")
def _sales_client(tmp_path):
    # Create isolated SQLite DB with minimal sales_invoices schema
    db_file = tmp_path / "test_sales.db"
    con = sqlite3.connect(db_file)
    cur = con.cursor()
    cur.execute(
        """
        CREATE TABLE sales_invoices (
          id INTEGER PRIMARY KEY,
          invoice_number TEXT,
          invoice_date TEXT,
          customer_rut TEXT,
          customer_name TEXT,
          total_amount REAL,
          currency TEXT,
          status TEXT,
          source_platform TEXT,
          project_id TEXT
        );
        """
    )
    # Insert sample rows
    rows = [
        (
            "F001", "2025-09-01", "11111111-1", "ACME", 1000.0,
            "CLP", "open", "sys", "10"
        ),
        (
            "F002", "2025-09-05", "22222222-2", "BETA", 2000.0,
            "USD", "paid", "sys", "11"
        ),
        (
            "F003", "2025-09-10", "11111111-1", "ACME", 500.0,
            "CLP", "open", "sys", None
        ),
    ]
    cur.executemany(
        (
            "INSERT INTO sales_invoices("
            "invoice_number, invoice_date, customer_rut, customer_name, "
            "total_amount, currency, status, source_platform, project_id) "
            "VALUES(?,?,?,?,?,?,?,?,?)"
        ),
        rows,
    )
    con.commit()
    con.close()
    os.environ['DB_PATH'] = str(db_file)
    server.app.config['TESTING'] = True
    with server.app.test_client() as c:
        yield c


def test_list_sales_invoices_basic_pagination(sales_client):
    rv = sales_client.get(
        '/api/sales_invoices?page=1&page_size=2&order_by=fecha&order_dir=ASC'
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['meta']['total'] == 3
    assert data['meta']['pages'] == 2
    assert len(data['items']) == 2


def test_list_sales_invoices_filters_and_search(sales_client):
    # Filter by rut
    rv = sales_client.get('/api/sales_invoices?rut=11111111-1')
    assert rv.status_code == 200
    data = rv.get_json()
    assert all(it['cliente_rut'] == '11111111-1' for it in data['items'])

    # Search by invoice number fragment
    rv = sales_client.get('/api/sales_invoices?search=F002')
    assert rv.status_code == 200
    data = rv.get_json()
    assert any(it['documento_numero'] == 'F002' for it in data['items'])


def test_list_sales_invoices_date_range_and_status(sales_client):
    rv = sales_client.get(
        '/api/sales_invoices?date_from=2025-09-02&date_to=2025-09-30'
    )
    assert rv.status_code == 200
    data = rv.get_json()
    # Should exclude F001 (2025-09-01)
    numeros = {it['documento_numero'] for it in data['items']}
    assert 'F001' not in numeros
    assert 'F002' in numeros and 'F003' in numeros


def test_list_sales_invoices_invalid_order_by_fallback(sales_client):
    rv = sales_client.get('/api/sales_invoices?order_by=__hack__')
    assert rv.status_code == 200
    # Fallback still returns data
    data = rv.get_json()
    assert 'items' in data


def test_ar_aging_empty_without_view(sales_client):
    rv = sales_client.get('/api/ar_aging_by_project')
    assert rv.status_code == 200
    assert rv.get_json()['items'] == []
