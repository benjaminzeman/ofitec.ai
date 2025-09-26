#!/usr/bin/env python3
"""
Revisar estructura de la tabla customers
"""
import sqlite3

def main():
    conn = sqlite3.connect("data/chipax_data.db")
    try:
        # Ver estructura de customers
        cursor = conn.execute("PRAGMA table_info(customers)")
        columns = cursor.fetchall()
        
        print("Estructura de tabla customers:")
        for col in columns:
            print(f"  {col[1]} ({col[2]}) - {col}")
        
        # Ver si la tabla existe y está vacía
        cursor = conn.execute("SELECT COUNT(*) FROM customers")
        count = cursor.fetchone()[0]
        print(f"\nRegistros en customers: {count}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()