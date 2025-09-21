#!/usr/bin/env python3
"""
Importa gastos desde CSV a la tabla canónica `expenses`.

Idempotencia:
- Si viene `comprobante`, se evita duplicar por ese campo.
- Si no, se considera combinación (fecha, monto, proveedor_rut, descripcion) como llave de existencia.

Uso:
  python tools/import_expenses.py --csv path/to/gastos.{csv|xlsx} \
    --db data/chipax_data.db \
    [--source CHIPAX] [--status validado]
"""

from __future__ import annotations

import argparse
import csv\nfrom io_utils import load_rows
import os
import sqlite3
from pathlib import Path
import sys

if __package__ in (None, ""):
    _here = Path(__file__).resolve().parent
    sys.path.append(str(_here))
from common_db import default_db_path
from rut_utils import normalize_rut, is_valid_rut


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          fecha TEXT,
          categoria TEXT,
          descripcion TEXT,
          monto REAL,
          moneda TEXT,
          proveedor_rut TEXT,
          proyecto TEXT,
          fuente TEXT,
          status TEXT,
          comprobante TEXT
        );
        """
    )
    # Índice auxiliar para búsquedas y evitar duplicados obvios por comprobante
    try:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_expenses_comprobante ON expenses(comprobante)"
        )
    except sqlite3.Error:
        pass


def norm_amount(v) -> float:
    try:
        if v is None or v == "":
            return 0.0
        return float(
            str(v).replace("$", "").replace(" ", "").replace(".", "").replace(",", ".")
        )
    except Exception:
        try:
            return float(v)
        except Exception:
            return 0.0


def upsert_expense(
    conn: sqlite3.Connection,
    r: dict,
    default_source: str | None,
    default_status: str | None,
    *,
    allow_invalid_rut: bool,
    counters: dict,
) -> None:
    cols = {c[1] for c in conn.execute("PRAGMA table_info(expenses)").fetchall()}

    fecha = r.get("Fecha") or r.get("fecha")
    categoria = r.get("Categoria") or r.get("categoria") or r.get("Categoría")
    descripcion = (
        r.get("Descripcion")
        or r.get("descripción")
        or r.get("descripcion")
        or r.get("Glosa")
        or r.get("glosa")
    )
    monto = norm_amount(r.get("Monto") or r.get("monto") or r.get("Total"))
    moneda = r.get("Moneda") or r.get("moneda") or "CLP"
    proveedor_rut_raw = (
        r.get("Proveedor_RUT") or r.get("RUT_Proveedor") or r.get("proveedor_rut") or r.get("RUT")
    )
    proveedor_rut = normalize_rut(proveedor_rut_raw)
    if proveedor_rut and not is_valid_rut(proveedor_rut):
        if not allow_invalid_rut:
            counters["invalid_rut"] = counters.get("invalid_rut", 0) + 1
            return
    proyecto = r.get("Proyecto") or r.get("proyecto")
    fuente = r.get("Fuente") or r.get("fuente") or default_source or "import"
    status = r.get("Estado") or r.get("status") or default_status or "emitido"
    comprobante = r.get("Comprobante") or r.get("comprobante") or r.get("Nro comprobante")

    # Detección por comprobante
    if comprobante:
        cur = conn.execute(
            "SELECT 1 FROM expenses WHERE comprobante = ?", (str(comprobante),)
        )
        if cur.fetchone():
            counters["duplicates"] = counters.get("duplicates", 0) + 1
            return

    # Detección por combinación si no hay comprobante
    where_parts, params = [], []
    for col, val in [
        ("fecha", fecha),
        ("monto", monto),
        ("proveedor_rut", proveedor_rut),
        ("descripcion", descripcion),
    ]:
        if col in cols and val not in (None, ""):
            where_parts.append(f"{col} = ?")
            params.append(val)
    if where_parts:
        cur = conn.execute(
            "SELECT 1 FROM expenses WHERE " + " AND ".join(where_parts), params
        )
        if cur.fetchone():
            counters["duplicates"] = counters.get("duplicates", 0) + 1
            return

    # Insert
    insert_cols, insert_vals, insert_params = [], [], []

    def add(col, val):
        if col in cols:
            insert_cols.append(col)
            insert_vals.append("?")
            insert_params.append(val)

    for col, val in [
        ("fecha", fecha),
        ("categoria", categoria),
        ("descripcion", descripcion),
        ("monto", monto),
        ("moneda", moneda),
        ("proveedor_rut", proveedor_rut),
        ("proyecto", proyecto),
        ("fuente", fuente),
        ("status", status),
        ("comprobante", comprobante),
    ]:
        add(col, val)

    sql = (
        "INSERT INTO expenses (" + ", ".join(insert_cols) + ") VALUES (" + ", ".join(insert_vals) + ")"
    )
    conn.execute(sql, insert_params)
    counters["inserted"] = counters.get("inserted", 0) + 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--db", default=default_db_path(prefer_root=False))
    ap.add_argument("--source", default="import")
    ap.add_argument("--status", default="emitido")
    ap.add_argument("--allow-invalid-rut", action="store_true", help="No rechazar RUT inválidos")
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print("DB not found:", db_path)
        return 2

    rows = load_rows(args.csv)

    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        counters: dict = {}
        for r in rows:
            upsert_expense(
                conn,
                r,
                args.source,
                args.status,
                allow_invalid_rut=args.allow_invalid_rut,
                counters=counters,
            )
        conn.commit()
        print(
            "Imported expenses:",
            counters.get("inserted", 0),
            "inserted,",
            counters.get("duplicates", 0),
            "duplicates,",
            counters.get("invalid_rut", 0),
            "invalid_rut",
        )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

