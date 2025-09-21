#!/usr/bin/env python3
"""
Importa cuentas bancarias desde CSV a `bank_accounts`.

Idempotencia: upsert por (bank_name, account_number).

Uso:
  python tools/import_bank_accounts.py --csv path/to/cuentas.csv \
    --db ofitec.ai/data/chipax_data.db
"""

from __future__ import annotations

import argparse
import csv
import os
import sqlite3
from pathlib import Path
import sys

if __package__ in (None, ""):
    _here = Path(__file__).resolve().parent
    sys.path.append(str(_here))
from common_db import default_db_path


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bank_accounts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          bank_name TEXT,
          account_number TEXT,
          currency TEXT,
          holder TEXT,
          alias TEXT
        );
        """
    )
    try:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_bank_account_unique ON bank_accounts(bank_name, account_number)"
        )
    except sqlite3.Error:
        pass


def upsert_account(conn: sqlite3.Connection, r: dict) -> None:
    cols = {c[1] for c in conn.execute("PRAGMA table_info(bank_accounts)").fetchall()}
    bank = r.get("Banco") or r.get("bank_name") or r.get("Bank")
    account = r.get("Cuenta") or r.get("account_number") or r.get("Account")
    currency = r.get("Moneda") or r.get("currency") or "CLP"
    holder = r.get("Titular") or r.get("holder") or r.get("Holder")
    alias = r.get("Alias") or r.get("alias")

    cur = conn.execute(
        "SELECT id FROM bank_accounts WHERE bank_name = ? AND account_number = ?",
        (bank, account),
    )
    row = cur.fetchone()
    if row:
        # Update minor fields
        parts, params = [], []
        if "currency" in cols:
            parts.append("currency = ?")
            params.append(currency)
        if "holder" in cols:
            parts.append("holder = ?")
            params.append(holder)
        if "alias" in cols:
            parts.append("alias = ?")
            params.append(alias)
        if parts:
            conn.execute(
                "UPDATE bank_accounts SET " + ", ".join(parts) + " WHERE id = ?",
                [*params, row[0]],
            )
        return

    insert_cols, insert_vals, insert_params = [], [], []
    def add(col, val):
        if col in cols:
            insert_cols.append(col)
            insert_vals.append("?")
            insert_params.append(val)
    for col, val in [
        ("bank_name", bank),
        ("account_number", account),
        ("currency", currency),
        ("holder", holder),
        ("alias", alias),
    ]:
        add(col, val)
    conn.execute(
        "INSERT INTO bank_accounts(" + ", ".join(insert_cols) + ") VALUES(" + ", ".join(insert_vals) + ")",
        insert_params,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--db", default=default_db_path(prefer_root=False))
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print("DB not found:", db_path)
        return 2

    with open(args.csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        n = 0
        for r in rows:
            upsert_account(conn, r)
            n += 1
        conn.commit()
        print(f"Imported/updated {n} bank accounts")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

