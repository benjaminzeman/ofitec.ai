#!/usr/bin/env python3
"""
Debug de proyectos
"""
import sqlite3

def main():
    conn = sqlite3.connect("data/chipax_data.db")
    try:
        print("=== DEBUG: Proyectos ===")
        
        # 1. Verificar vistas que busca el código
        vistas_buscadas = ["v_ordenes_compra", "v_presupuesto_totales"]
        
        for vista in vistas_buscadas:
            try:
                cursor = conn.execute(f"SELECT name FROM sqlite_master WHERE type='view' AND name='{vista}'")
                view_exists = cursor.fetchone()
                if view_exists:
                    print(f"✅ Vista {vista} existe")
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {vista}")
                    count = cursor.fetchone()[0]
                    print(f"  Registros: {count}")
                else:
                    print(f"❌ Vista {vista} NO existe")
            except Exception as e:
                print(f"❌ Error accediendo a {vista}: {e}")
        
        # 2. Verificar tabla purchase_orders_unified
        print("\n2. Tabla purchase_orders_unified:")
        try:
            cursor = conn.execute("PRAGMA table_info(purchase_orders_unified)")
            columns = [col[1] for col in cursor.fetchall()]
            print(f"Columnas: {columns}")
            
            cursor = conn.execute("SELECT COUNT(*) FROM purchase_orders_unified")
            count = cursor.fetchone()[0]
            print(f"Registros: {count}")
            
            # Ver si hay zoho_project_id o zoho_project_name
            if 'zoho_project_id' in columns:
                cursor = conn.execute("SELECT zoho_project_id, COUNT(*) FROM purchase_orders_unified WHERE zoho_project_id IS NOT NULL GROUP BY zoho_project_id")
                projects = cursor.fetchall()
                print(f"Proyectos por zoho_project_id: {projects}")
                
            if 'zoho_project_name' in columns:
                cursor = conn.execute("SELECT zoho_project_name, COUNT(*) FROM purchase_orders_unified WHERE zoho_project_name IS NOT NULL GROUP BY zoho_project_name")
                projects = cursor.fetchall()
                print(f"Proyectos por zoho_project_name: {projects}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # 3. Verificar tabla projects directamente
        print("\n3. Tabla projects:")
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM projects")
            count = cursor.fetchone()[0]
            print(f"Registros en projects: {count}")
            
            if count > 0:
                cursor = conn.execute("SELECT * FROM projects LIMIT 3")
                rows = cursor.fetchall()
                print(f"Primeros 3 proyectos: {rows}")
        except Exception as e:
            print(f"❌ Error: {e}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    main()