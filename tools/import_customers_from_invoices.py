#!/usr/bin/env python3
"""
Importa clientes desde archivos CSV de Facturas Venta a la tabla customers.

Extrae información de clientes (RUT + Razón Social) de los archivos de Facturas Venta.

Uso:
  python tools/import_customers_from_invoices.py --db data/chipax_data.db

Reglas:
- Procesa todos los archivos *Facturas venta*.csv de data/raw/chipax/
- Extrae RUT y Razón Social de las facturas
- Normaliza RUT y nombres
- Idempotencia: UNIQUE por rut_clean evita duplicados
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import sqlite3
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent))

from rut_utils import normalize_rut
from common_db import default_db_path


def ensure_table(conn: sqlite3.Connection) -> None:
    # La tabla customers ya existe, solo verificamos el índice
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_customer_rut ON customers(rut_clean)"
    )


def norm_name(name: str | None) -> str:
    if not name:
        return ""
    try:
        import unicodedata
        n = unicodedata.normalize("NFKD", name)
        n = "".join(ch for ch in n if not unicodedata.combining(ch))
        return n.strip().upper()
    except (UnicodeError, AttributeError):
        return name.strip().upper()


def extract_customers_from_invoice_file(file_path: str) -> list[dict]:
    """Extrae información de clientes de un archivo de facturas de venta"""
    customers = {}
    
    try:
        with open(file_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rut_raw = row.get("RUT", "").strip()
                name_raw = row.get("Razón Social", "").strip()
                
                if not rut_raw or not name_raw:
                    continue
                    
                rut_clean = normalize_rut(rut_raw)
                if not rut_clean:
                    continue
                    
                name_norm = norm_name(name_raw)
                if not name_norm:
                    continue
                
                # Usar el RUT como key para evitar duplicados dentro del mismo archivo
                if rut_clean not in customers:
                    customers[rut_clean] = {
                        "rut_clean": rut_clean,
                        "name_normalized": name_norm,
                        "original_name": name_raw
                    }
    except (IOError, csv.Error, UnicodeError) as e:
        print(f"Error procesando {file_path}: {e}")
        return []
    
    return list(customers.values())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=default_db_path(prefer_root=False))
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print("DB not found:", db_path)
        return 2

    # Buscar todos los archivos de Facturas venta
    pattern = "data/raw/chipax/*Facturas venta*.csv"
    invoice_files = glob.glob(pattern)
    
    if not invoice_files:
        print(f"No se encontraron archivos con patrón: {pattern}")
        return 1
        
    print(f"Encontrados {len(invoice_files)} archivos de facturas de venta")

    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        
        all_customers = {}
        total_processed = 0
        
        # Procesar todos los archivos
        for file_path in invoice_files:
            print(f"Procesando: {os.path.basename(file_path)}")
            customers = extract_customers_from_invoice_file(file_path)
            
            for customer in customers:
                rut = customer["rut_clean"]
                if rut not in all_customers:
                    all_customers[rut] = customer
                    total_processed += 1

        print(f"Total clientes únicos extraídos: {len(all_customers)}")
        
        # Insertar en la base de datos
        inserted = updated = skipped = 0
        for customer in all_customers.values():
            rut = customer["rut_clean"]
            name_norm = customer["name_normalized"]
            
            # Verificar si ya existe
            cur = conn.execute("SELECT name_normalized FROM customers WHERE rut_clean = ?", (rut,))
            row = cur.fetchone()
            
            if row:
                if row[0] != name_norm:
                    conn.execute(
                        "UPDATE customers SET name_normalized = ? WHERE rut_clean = ?",
                        (name_norm, rut),
                    )
                    updated += 1
                else:
                    skipped += 1
            else:
                conn.execute(
                    "INSERT INTO customers (rut_clean, name_normalized) VALUES (?, ?)",
                    (rut, name_norm),
                )
                inserted += 1
        
        conn.commit()
        print(f"Customers -> inserted: {inserted}, updated: {updated}, skipped: {skipped}")
        return 0
        
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())