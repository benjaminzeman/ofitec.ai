#!/usr/bin/env python3
"""
Script para verificar fechas de facturas y sugerir corrección
"""
import sqlite3

def analyze_invoice_dates():
    """Analiza las fechas de las facturas para ajustar consultas"""
    conn = sqlite3.connect("data/chipax_data.db")
    try:
        print("=== ANÁLISIS: Fechas de Facturas ===")
        
        # Ver distribución de años en facturas de venta
        cursor = conn.execute("""
            SELECT strftime('%Y', fecha) as year, 
                   COUNT(*) as count,
                   SUM(monto_total) as total_revenue
            FROM v_facturas_venta 
            WHERE fecha IS NOT NULL
            GROUP BY strftime('%Y', fecha)
            ORDER BY year DESC
        """)
        
        years = cursor.fetchall()
        print("Distribución por año:")
        total_all_time = 0
        for year, count, revenue in years:
            print(f"  {year}: {count} facturas, ${revenue:,.2f}")
            total_all_time += revenue or 0
        
        print(f"\nTotal histórico: ${total_all_time:,.2f}")
        
        # Ver último año con datos significativos
        if years:
            last_year_with_data = years[0][0]  # Primer año (más reciente)
            print(f"\nÚltimo año con datos: {last_year_with_data}")
            
            # Revenue del último año
            cursor = conn.execute(f"""
                SELECT SUM(monto_total) 
                FROM v_facturas_venta 
                WHERE strftime('%Y', fecha) = '{last_year_with_data}'
            """)
            last_year_revenue = cursor.fetchone()[0]
            print(f"Revenue {last_year_with_data}: ${last_year_revenue:,.2f}")
            
            # Revenue último mes del último año con datos
            cursor = conn.execute(f"""
                SELECT strftime('%Y-%m', fecha) as month,
                       SUM(monto_total) as revenue
                FROM v_facturas_venta 
                WHERE strftime('%Y', fecha) = '{last_year_with_data}'
                GROUP BY strftime('%Y-%m', fecha)
                ORDER BY month DESC
                LIMIT 1
            """)
            last_month_data = cursor.fetchone()
            if last_month_data:
                month, revenue = last_month_data
                print(f"Último mes con datos: {month} - ${revenue:,.2f}")
        
        return years
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []
    finally:
        conn.close()

def test_corrected_queries():
    """Prueba consultas corregidas usando el último año con datos"""
    conn = sqlite3.connect("data/chipax_data.db")
    try:
        print("\n=== PRUEBA: Consultas Corregidas ===")
        
        # Usar 2024 como año de referencia (último año con datos según nuestro análisis previo)
        test_year = "2024"
        
        # Revenue del último año completo
        cursor = conn.execute(f"""
            SELECT SUM(monto_total) 
            FROM v_facturas_venta 
            WHERE strftime('%Y', fecha) = '{test_year}'
        """)
        year_revenue = cursor.fetchone()[0] or 0
        print(f"Revenue {test_year}: ${year_revenue:,.2f}")
        
        # Revenue último trimestre
        cursor = conn.execute(f"""
            SELECT SUM(monto_total) 
            FROM v_facturas_venta 
            WHERE fecha >= '{test_year}-10-01' AND fecha <= '{test_year}-12-31'
        """)
        q4_revenue = cursor.fetchone()[0] or 0
        print(f"Q4 {test_year}: ${q4_revenue:,.2f}")
        
        # Revenue último mes con datos
        cursor = conn.execute(f"""
            SELECT SUM(monto_total) 
            FROM v_facturas_venta 
            WHERE strftime('%Y-%m', fecha) = '{test_year}-12'
        """)
        last_month_revenue = cursor.fetchone()[0] or 0
        print(f"Diciembre {test_year}: ${last_month_revenue:,.2f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    analyze_invoice_dates()
    test_corrected_queries()