"""
Verificar tablas en la base de datos
"""
import sqlite3

def verificar_tablas():
    db_path = r"c:\Odoo\custom_addons\ofitec_dev.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Listar todas las tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("Tablas en la base de datos:")
        for table in tables:
            print(f"  - {table[0]}")
            
        # Verificar tabla de chipax más específicamente
        chipax_tables = [t[0] for t in tables if 'chipax' in t[0].lower()]
        if chipax_tables:
            print(f"\nTablas de Chipax encontradas:")
            for table in chipax_tables:
                print(f"  - {table}")
                
                # Mostrar estructura de la tabla
                cursor.execute(f"PRAGMA table_info({table});")
                columns = cursor.fetchall()
                print(f"    Columnas: {[col[1] for col in columns]}")
                
                # Contar registros
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                print(f"    Registros: {count}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verificar_tablas()