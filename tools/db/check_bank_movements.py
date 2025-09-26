#!/usr/bin/env python3
"""
Revisar estructura de la tabla bank_movements
"""
import sqlite3

def main():
    conn = sqlite3.connect("data/chipax_data.db")
    try:
        # Ver estructura de bank_movements
        cursor = conn.execute("PRAGMA table_info(bank_movements)")
        columns = cursor.fetchall()
        
        print("Estructura de tabla bank_movements:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # Ver algunos registros de ejemplo
        cursor = conn.execute("SELECT * FROM bank_movements LIMIT 3")
        rows = cursor.fetchall()
        print(f"\nPrimeros 3 registros:")
        for i, row in enumerate(rows):
            print(f"  Registro {i+1}: {row}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()