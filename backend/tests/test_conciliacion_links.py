import os
import sqlite3
import tempfile

from server import app

# Cada test obtiene su propia BD temporal


def _new_db():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    os.environ["DB_PATH"] = tmp.name
    con = sqlite3.connect(tmp.name)
    return con, tmp.name


def _base_schema(cur):
    cur.executescript(
        """
        CREATE TABLE recon_links(
            id INTEGER PRIMARY KEY,
            reconciliation_id INTEGER,
            bank_movement_id INTEGER,
            sales_invoice_id INTEGER,
            purchase_invoice_id INTEGER,
            expense_id INTEGER,
            payroll_id INTEGER,
            tax_id INTEGER,
            amount REAL
        );
        CREATE TABLE sales_invoices(
            id INTEGER PRIMARY KEY,
            invoice_number TEXT,
            invoice_date TEXT
        );
        CREATE TABLE ap_invoices(
            id INTEGER PRIMARY KEY,
            invoice_number TEXT,
            invoice_date TEXT
        );
        CREATE TABLE expenses(
            id INTEGER PRIMARY KEY,
            descripcion TEXT,
            fecha TEXT
        );
        CREATE TABLE taxes(
            id INTEGER PRIMARY KEY,
            tipo TEXT,
            periodo TEXT
        );
        CREATE TABLE bank_movements(
            id INTEGER PRIMARY KEY,
            referencia TEXT,
            glosa TEXT,
            fecha TEXT
        );
        CREATE TABLE payroll_slips(
            id INTEGER PRIMARY KEY,
            periodo TEXT,
            rut_trabajador TEXT
        );
        """
    )


def test_links_empty_when_no_params():
    con, path = _new_db()
    try:
        _base_schema(con.cursor())
        con.commit()
        client = app.test_client()
        r = client.get("/api/conciliacion/links")
        assert r.status_code == 200
        assert r.get_json()["items"] == []
    finally:
        con.close()
        os.remove(path)


def test_links_bank_id_anchor():
    con, path = _new_db()
    cur = con.cursor()
    _base_schema(cur)
    cur.executescript(
        """
        INSERT INTO sales_invoices(id, invoice_number, invoice_date)
        VALUES (1,'S-1','2025-01-05');
        INSERT INTO bank_movements(id, referencia, glosa, fecha)
        VALUES (10,'REF10','GM','2025-01-06');
        INSERT INTO recon_links(
          id, reconciliation_id, bank_movement_id, sales_invoice_id, amount
        ) VALUES (100,1,10,1,123.45);
        """
    )
    con.commit()
    r = app.test_client().get("/api/conciliacion/links?bank_id=10")
    data = r.get_json()["items"]
    assert len(data) == 1
    assert data[0]["type"] == "sales"
    assert data[0]["ref"] == "S-1"
    con.close()
    os.remove(path)


def test_links_sales_doc_date_anchor():
    con, path = _new_db()
    cur = con.cursor()
    _base_schema(cur)
    cur.executescript(
        """
        INSERT INTO sales_invoices(id, invoice_number, invoice_date)
        VALUES (1,'S-9','2025-02-01');
        INSERT INTO bank_movements(id, referencia, glosa, fecha)
        VALUES (5,'REF5','BM','2025-02-02');
        INSERT INTO recon_links(
          id, reconciliation_id, bank_movement_id, sales_invoice_id, amount
        ) VALUES (200,1,5,1,50.0);
        """
    )
    con.commit()
    r = app.test_client().get(
        "/api/conciliacion/links?sales_doc=S-9&sales_date=2025-02-01"
    )
    data = r.get_json()["items"]
    assert len(data) == 1
    assert data[0]["type"] == "bank"  # inverted perspective
    assert data[0]["ref"] == "REF5"
    con.close()
    os.remove(path)


def test_links_purchase_doc_date_anchor():
    con, path = _new_db()
    cur = con.cursor()
    _base_schema(cur)
    cur.executescript(
        """
        INSERT INTO ap_invoices(id, invoice_number, invoice_date)
        VALUES (1,'P-1','2025-03-01');
        INSERT INTO sales_invoices(id, invoice_number, invoice_date)
        VALUES (2,'S-2','2025-03-02');
        INSERT INTO recon_links(
          id, reconciliation_id, sales_invoice_id, purchase_invoice_id, amount
        ) VALUES (300,1,2,1,75.0);
        """
    )
    con.commit()
    r = app.test_client().get(
        "/api/conciliacion/links?purchase_doc=P-1&purchase_date=2025-03-01"
    )
    data = r.get_json()["items"]
    assert len(data) == 1
    assert data[0]["type"] == "sales"
    assert data[0]["ref"] == "S-2"
    con.close()
    os.remove(path)


def test_links_expense_id_anchor():
    con, path = _new_db()
    cur = con.cursor()
    _base_schema(cur)
    cur.executescript(
        """
        INSERT INTO expenses(id, descripcion, fecha)
        VALUES (10,'Taxi','2025-04-10');
        INSERT INTO recon_links(
          id, reconciliation_id, expense_id, amount
        ) VALUES (400,1,10,10.0);
        """
    )
    con.commit()
    r = app.test_client().get("/api/conciliacion/links?expense_id=10")
    data = r.get_json()["items"]
    assert len(data) == 1
    assert data[0]["type"] == "expense"
    assert data[0]["ref"] == "Taxi"
    con.close()
    os.remove(path)


def test_links_payroll_id_anchor():
    con, path = _new_db()
    cur = con.cursor()
    _base_schema(cur)
    cur.executescript(
        """
        INSERT INTO payroll_slips(id, periodo, rut_trabajador)
        VALUES (5,'2025-05','11-1');
        INSERT INTO recon_links(
          id, reconciliation_id, payroll_id, amount
        ) VALUES (500,1,5,300.0);
        """
    )
    con.commit()
    r = app.test_client().get("/api/conciliacion/links?payroll_id=5")
    data = r.get_json()["items"]
    assert len(data) == 1
    assert data[0]["type"] == "payroll"
    con.close()
    os.remove(path)


def test_links_payroll_period_rut_anchor():
    con, path = _new_db()
    cur = con.cursor()
    _base_schema(cur)
    cur.executescript(
        """
        INSERT INTO payroll_slips(id, periodo, rut_trabajador)
        VALUES (6,'2025-06','22-2');
        INSERT INTO recon_links(
          id, reconciliation_id, payroll_id, amount
        ) VALUES (510,1,6,325.0);
        """
    )
    con.commit()
    r = app.test_client().get(
        "/api/conciliacion/links?payroll_period=2025-06&payroll_rut=22-2"
    )
    data = r.get_json()["items"]
    assert len(data) == 1
    assert data[0]["type"] == "payroll"
    con.close()
    os.remove(path)


def test_links_tax_id_anchor():
    con, path = _new_db()
    cur = con.cursor()
    _base_schema(cur)
    cur.executescript(
        """
        INSERT INTO taxes(id, tipo, periodo) VALUES (9,'IVA','2025-07');
        INSERT INTO recon_links(id, reconciliation_id, tax_id, amount)
        VALUES (600,1,9,500.0);
        """
    )
    con.commit()
    r = app.test_client().get("/api/conciliacion/links?tax_id=9")
    data = r.get_json()["items"]
    assert len(data) == 1
    assert data[0]["type"] == "tax"
    con.close()
    os.remove(path)


def test_links_tax_period_tipo_anchor():
    con, path = _new_db()
    cur = con.cursor()
    _base_schema(cur)
    cur.executescript(
        """
        INSERT INTO taxes(id, tipo, periodo) VALUES (10,'RLI','2025-08');
        INSERT INTO recon_links(id, reconciliation_id, tax_id, amount)
        VALUES (610,1,10,800.0);
        """
    )
    con.commit()
    r = app.test_client().get(
        "/api/conciliacion/links?tax_period=2025-08&tax_tipo=RLI"
    )
    data = r.get_json()["items"]
    assert len(data) == 1
    assert data[0]["type"] == "tax"
    con.close()
    os.remove(path)
