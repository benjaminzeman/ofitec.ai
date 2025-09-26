#!/usr/bin/env python3
"""Script para revisar el contenido de la base de datos."""

from db_utils import db_conn

def main():
    with db_conn() as conn:
        cursor = conn.cursor()
        
        # Listar todas las tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print("Tablas disponibles:")
        for table in tables:
            table_name = table[0]
            print(f"- {table_name}")
            
            # Contar registros en cada tabla
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  └─ {count} registros")
            
            # Si es la tabla de movimientos bancarios, mostrar algunos ejemplos
            if table_name == "bank_movements":
                print("  └─ Primeros 5 registros:")
                cursor.execute("SELECT * FROM bank_movements LIMIT 5")
                rows = cursor.fetchall()
                for row in rows:
                    print(f"    {dict(row)}")

if __name__ == "__main__":
    main()