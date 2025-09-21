import os
import sqlite3
from datetime import datetime

import pytest

from services.conciliacion_bancaria.core import integration


@pytest.fixture(autouse=True)
def _clear_db_path(monkeypatch):
    monkeypatch.delenv("DB_PATH", raising=False)


def test_system_creates_tables_and_initializes_engine(tmp_path, monkeypatch):
    ofitec_db = tmp_path / "ofitec.db"
    chipax_db = tmp_path / "chipax.db"

    # Create empty Chipax DB so the system detects it
    sqlite3.connect(chipax_db).close()

    sentinel = object()
    recorded = {}

    def fake_init_ml(db_path: str):
        recorded["path"] = db_path
        return sentinel

    monkeypatch.setattr(integration, "initialize_ml_engine", fake_init_ml)
    monkeypatch.setattr(integration, "ML_AVAILABLE", True)

    system = integration.OfitecReconciliationSystem(
        str(ofitec_db), str(chipax_db)
    )

    assert system.ml_engine is sentinel
    assert recorded["path"] == str(ofitec_db)
    assert ofitec_db.exists()

    with sqlite3.connect(ofitec_db) as con:
        names = {
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert {
        "ofitec_cuentas_corrientes",
        "ofitec_movimientos_banco",
        "ofitec_aliases_contraparte",
    }.issubset(names)


def test_import_chipax_data_populates_bank_movements(tmp_path, monkeypatch):
    ofitec_db = tmp_path / "ofitec.db"
    chipax_db = tmp_path / "chipax.db"

    rows = [
        (
            "2024-02-01",
            "TRANSFERENCIA CLIENTE ALFA 12345678-9",
            125000.0,
            "abono",
            "REF-1",
            "12345678-9",
            "Cliente Alfa",
        ),
        (
            "2024-02-03",
            "PAGO PROVEEDOR BETA 98765432-1",
            -85000.0,
            "cargo",
            "REF-2",
            "98765432-1",
            "Proveedor Beta",
        ),
    ]

    with sqlite3.connect(chipax_db) as con:
        con.execute(
            """
            CREATE TABLE movimientos_chipax (
                fecha TEXT,
                descripcion TEXT,
                monto REAL,
                tipo TEXT,
                referencia TEXT,
                rut_emisor TEXT,
                nombre_emisor TEXT
            )
            """
        )
        con.executemany(
            """
            INSERT INTO movimientos_chipax(
                fecha, descripcion, monto, tipo,
                referencia, rut_emisor, nombre_emisor
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        con.commit()

    monkeypatch.setattr(integration, "ML_AVAILABLE", True)
    monkeypatch.setattr(
        integration,
        "initialize_ml_engine",
        lambda db_path: "engine",
    )

    system = integration.OfitecReconciliationSystem(
        str(ofitec_db), str(chipax_db)
    )

    result = system.import_chipax_data()
    assert result["success"] is True
    assert result["total_chipax_transactions"] == len(rows)
    assert result["imported_bank_movements"] == len(rows)

    with sqlite3.connect(ofitec_db) as con:
        bank_count = con.execute(
            "SELECT COUNT(*) FROM ofitec_movimientos_banco"
        ).fetchone()[0]
        status_count = con.execute(
            "SELECT COUNT(*) FROM ofitec_estado_conciliacion"
        ).fetchone()[0]
        assert bank_count == len(rows)
        assert status_count == 1

