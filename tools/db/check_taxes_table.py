#!/usr/bin/env python3
"""
Revisar estructura de la tabla taxes
"""
import sqlite3

def main():
    conn = sqlite3.connect("data/chipax_data.db")
    try:
        # Ver estructura de taxes
        cursor = conn.execute("PRAGMA table_info(taxes)")
        columns = cursor.fetchall()
        
        print("Estructura de tabla taxes:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # Ver registros existentes
        cursor = conn.execute("SELECT COUNT(*) FROM taxes")
        count = cursor.fetchone()[0]
        print(f"\nRegistros en taxes: {count}")
        
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()