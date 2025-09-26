import sqlite3
import os

# Conectar a la base de datos
db_path = r"c:\Ofitec\ofitec.ai\data\chipax_data.db"
print(f"Conectando a: {db_path}")
print(f"Archivo existe: {os.path.exists(db_path)}")
print(f"Tamaño: {os.path.getsize(db_path)} bytes")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Listar todas las tablas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("\nTablas disponibles:")
for table in tables:
    table_name = table[0]
    print(f"- {table_name}")
    
    # Contar registros en cada tabla
    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
    count = cursor.fetchone()[0]
    print(f"  └─ {count} registros")

# Verificar específicamente la tabla bank_movements
print("\n=== Tabla bank_movements ===")
try:
    cursor.execute("SELECT COUNT(*) FROM bank_movements")
    count = cursor.fetchone()[0]
    print(f"Registros en bank_movements: {count}")
    
    if count > 0:
        print("\nPrimeros 5 registros:")
        cursor.execute("SELECT * FROM bank_movements LIMIT 5")
        rows = cursor.fetchall()
        
        # Obtener nombres de columnas
        cursor.execute("PRAGMA table_info(bank_movements)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Columnas: {columns}")
        
        for i, row in enumerate(rows):
            print(f"Registro {i+1}: {dict(zip(columns, row))}")
except sqlite3.Error as e:
    print(f"Error consultando bank_movements: {e}")

conn.close()