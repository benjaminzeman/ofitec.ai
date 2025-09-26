#!/usr/bin/env python3
"""
Debug del cálculo de Revenue
"""
import sqlite3

def main():
    conn = sqlite3.connect("data/chipax_data.db")
    try:
        print("=== DEBUG: Revenue ===")
        
        # 1. Verificar si existe la vista v_facturas_venta
        print("\n1. Verificar vista v_facturas_venta:")
        try:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='v_facturas_venta'")
            view_exists = cursor.fetchone()
            if view_exists:
                print("✅ Vista v_facturas_venta existe")
                
                # Ver estructura
                cursor = conn.execute("PRAGMA table_info(v_facturas_venta)")
                columns = [col[1] for col in cursor.fetchall()]
                print(f"Columnas: {columns}")
                
                # Ver datos
                cursor = conn.execute("SELECT COUNT(*) FROM v_facturas_venta")
                count = cursor.fetchone()[0]
                print(f"Registros en vista: {count}")
                
            else:
                print("❌ Vista v_facturas_venta NO existe")
        except Exception as e:
            print(f"❌ Error accediendo a vista: {e}")
        
        # 2. Verificar tabla sales_invoices directamente
        print("\n2. Verificar tabla sales_invoices:")
        cursor = conn.execute("PRAGMA table_info(sales_invoices)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Columnas disponibles: {columns}")
        
        cursor = conn.execute("SELECT COUNT(*) FROM sales_invoices")
        count = cursor.fetchone()[0]
        print(f"Total registros: {count}")
        
        # Ver fechas disponibles
        if 'fecha' in columns or 'fecha_emision' in columns:
            fecha_col = 'fecha' if 'fecha' in columns else 'fecha_emision'
            cursor = conn.execute(f"SELECT {fecha_col}, COUNT(*) FROM sales_invoices WHERE {fecha_col} IS NOT NULL GROUP BY {fecha_col} ORDER BY {fecha_col} DESC LIMIT 5")
            dates = cursor.fetchall()
            print(f"Fechas más recientes ({fecha_col}): {dates}")
            
            # Ver montos
            monto_cols = [col for col in columns if 'monto' in col.lower() or 'total' in col.lower()]
            print(f"Columnas de monto: {monto_cols}")
            
            for col in monto_cols[:3]:  # Primeras 3 columnas de monto
                cursor = conn.execute(f"SELECT SUM({col}) FROM sales_invoices WHERE {col} IS NOT NULL")
                total = cursor.fetchone()[0]
                print(f"Suma {col}: {total}")
        
        # 3. Probar consulta del CEO endpoint para mes actual
        print("\n3. Consulta mes actual (como CEO endpoint):")
        try:
            cursor = conn.execute(
                "SELECT SUM(monto_total) FROM v_facturas_venta WHERE strftime('%Y-%m', fecha)=strftime('%Y-%m','now')"
            )
            month = cursor.fetchone()[0]
            print(f"Facturación mes actual: {month}")
            
            cursor = conn.execute(
                "SELECT SUM(monto_total) FROM v_facturas_venta WHERE date(fecha)>=date(strftime('%Y-01-01','now'))"
            )
            ytd = cursor.fetchone()[0]
            print(f"Facturación YTD: {ytd}")
        except Exception as e:
            print(f"❌ Error en consulta CEO: {e}")
        
        # 4. Verificar con fecha actual manualmente
        print("\n4. Verificar con fecha 2025:")
        current_month = "2025-09"
        try:
            cursor = conn.execute(
                f"SELECT SUM(monto_total) FROM sales_invoices WHERE strftime('%Y-%m', fecha_emision) = '{current_month}'"
            )
            month_direct = cursor.fetchone()[0]
            print(f"Facturación directa sales_invoices Sept 2025: {month_direct}")
        except Exception as e:
            print(f"❌ Error consulta directa: {e}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    main()