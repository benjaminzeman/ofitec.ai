#!/usr/bin/env python3
"""
Importa cuentas bancarias desde datos existentes en bank_movements.

Extrae información única de bancos y cuentas desde la tabla bank_movements
para poblar la tabla bank_accounts.

Uso:
  python tools/import_bank_accounts_from_movements.py --db data/chipax_data.db
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
    # La tabla bank_accounts ya existe, solo verificamos el índice
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_bank_account_unique ON bank_accounts(bank_name, account_number)"
    )


def extract_bank_accounts(conn: sqlite3.Connection) -> list[dict]:
    """Extrae cuentas bancarias únicas de bank_movements"""
    cursor = conn.execute(
        """
        SELECT DISTINCT
            bank_name,
            account_number,
            moneda AS currency
        FROM bank_movements
        WHERE bank_name IS NOT NULL
          AND account_number IS NOT NULL
          AND bank_name != ''
          AND account_number != ''
        ORDER BY bank_name, account_number
        """
    )
    
    accounts = []
    for row in cursor.fetchall():
        bank_name, account_number, currency = row
        accounts.append({
            "bank_name": bank_name,
            "account_number": account_number,
            "currency": currency or "CLP",
            "holder": "OFITEC SPA",  # Asumiendo que es la empresa titular
            "alias": f"{bank_name} - {account_number}"
        })
    
    return accounts


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
        
        # Extraer cuentas bancarias de los movimientos
        accounts = extract_bank_accounts(conn)
        print(f"Encontradas {len(accounts)} cuentas bancarias únicas en movimientos")
        
        if not accounts:
            print("No se encontraron cuentas bancarias válidas en bank_movements")
            return 1
        
        # Insertar en la base de datos
        inserted = updated = skipped = 0
        
        for account in accounts:
            bank_name = account["bank_name"]
            account_number = account["account_number"]
            currency = account["currency"]
            holder = account["holder"]
            alias = account["alias"]
            
            # Verificar si ya existe
            cur = conn.execute(
                "SELECT id FROM bank_accounts WHERE bank_name = ? AND account_number = ?",
                (bank_name, account_number)
            )
            row = cur.fetchone()
            
            if row:
                # Actualizar campos opcionales
                conn.execute(
                    """UPDATE bank_accounts 
                       SET currency = ?, holder = ?, alias = ? 
                       WHERE bank_name = ? AND account_number = ?""",
                    (currency, holder, alias, bank_name, account_number)
                )
                updated += 1
            else:
                conn.execute(
                    """INSERT INTO bank_accounts (bank_name, account_number, currency, holder, alias) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (bank_name, account_number, currency, holder, alias)
                )
                inserted += 1
        
        conn.commit()
        print(f"Bank accounts -> inserted: {inserted}, updated: {updated}, skipped: {skipped}")
        return 0
        
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())