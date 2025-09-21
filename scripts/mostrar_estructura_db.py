import sqlite3
import pandas as pd

def mostrar_estructura_db():
    """Mostrar la estructura de la base de datos actual"""
    db_path = r"c:\Odoo\custom_addons\ofitec_dev.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Obtener todas las tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("="*60)
        print("ESTRUCTURA BASE DE DATOS OFITEC_DEV.DB")
        print("="*60)
        
        for table in tables:
            table_name = table[0]
            print(f"\n📊 TABLA: {table_name}")
            
            # Contar registros
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"   Registros: {count:,}")
            
            # Obtener estructura
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            print("   Columnas:")
            for col in columns[:10]:  # Mostrar primeras 10 columnas
                print(f"     - {col[1]} ({col[2]})")
            
            if len(columns) > 10:
                print(f"     ... y {len(columns) - 10} columnas más")
        
        # Obtener vistas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view';")
        views = cursor.fetchall()
        
        if views:
            print(f"\n🔍 VISTAS:")
            for view in views:
                print(f"   - {view[0]}")
        
        conn.close()
        
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    mostrar_estructura_db()