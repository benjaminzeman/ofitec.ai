#!/usr/bin/env python3
"""
Importa configuración básica de impuestos para Chile.

Crea registros básicos de impuestos chilenos en la tabla taxes.

Uso:
  python tools/import_chile_taxes.py --db data/chipax_data.db
"""
from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent))

from common_db import default_db_path


def ensure_table(conn: sqlite3.Connection) -> None:
    """La tabla taxes ya existe con estructura diferente, no la modificamos"""
    pass


def get_sample_tax_declarations() -> list[dict]:
    """Define declaraciones de impuestos de ejemplo para Chile"""
    import datetime
    current_year = datetime.datetime.now().year
    
    return [
        {
            "periodo": f"{current_year}-01",
            "tipo": "IVA",
            "monto_debito": 5000000.0,
            "monto_credito": 950000.0,
            "neto": 4050000.0,
            "estado": "PRESENTADO",
            "fecha_presentacion": f"{current_year}-02-12",
            "fuente": "SISTEMA"
        },
        {
            "periodo": f"{current_year}-02",
            "tipo": "IVA",
            "monto_debito": 4800000.0,
            "monto_credito": 912000.0,
            "neto": 3888000.0,
            "estado": "PRESENTADO", 
            "fecha_presentacion": f"{current_year}-03-12",
            "fuente": "SISTEMA"
        },
        {
            "periodo": f"{current_year}-03",
            "tipo": "IVA",
            "monto_debito": 5200000.0,
            "monto_credito": 988000.0,
            "neto": 4212000.0,
            "estado": "PRESENTADO",
            "fecha_presentacion": f"{current_year}-04-12",
            "fuente": "SISTEMA"
        }
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=default_db_path(prefer_root=False))
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print("DB not found:", db_path)
        return 2

    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        
        taxes = get_sample_tax_declarations()
        print(f"Configurando {len(taxes)} declaraciones de impuestos de ejemplo")
        
        inserted = updated = skipped = 0
        
        for tax in taxes:
            periodo = tax["periodo"]
            tipo = tax["tipo"]
            
            # Verificar si ya existe
            cur = conn.execute(
                "SELECT neto FROM taxes WHERE periodo = ? AND tipo = ?", 
                (periodo, tipo)
            )
            row = cur.fetchone()
            
            if row:
                skipped += 1
            else:
                conn.execute(
                    """INSERT INTO taxes 
                       (periodo, tipo, monto_debito, monto_credito, neto, estado, fecha_presentacion, fuente) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tax["periodo"], tax["tipo"], tax["monto_debito"], 
                        tax["monto_credito"], tax["neto"], tax["estado"],
                        tax["fecha_presentacion"], tax["fuente"]
                    ),
                )
                inserted += 1
        
        conn.commit()
        print(f"Taxes -> inserted: {inserted}, updated: {updated}, skipped: {skipped}")
        return 0
        
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())