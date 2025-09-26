#!/usr/bin/env python3
"""
Debug de las consultas corregidas del CEO endpoint
"""
import sqlite3

def debug_ceo_queries():
    """Debug paso a paso de las consultas CEO"""
    conn = sqlite3.connect("data/chipax_data.db")
    try:
        print("=== DEBUG: Consultas CEO Corregidas ===")
        
        # 1. Probar consulta de último período
        print("\n1. Buscar último período con datos significativos:")
        cursor = conn.execute("""
            SELECT strftime('%Y-%m', fecha) as period
            FROM v_facturas_venta 
            WHERE fecha IS NOT NULL
            GROUP BY strftime('%Y-%m', fecha)
            HAVING COUNT(*) >= 2  -- Al menos 2 facturas para ser significativo
            ORDER BY period DESC
            LIMIT 1
        """)
        latest_period_row = cursor.fetchone()
        
        if latest_period_row:
            latest_period = latest_period_row[0]
            print(f"✅ Último período encontrado: {latest_period}")
            
            latest_year = latest_period.split('-')[0]
            latest_month = int(latest_period.split('-')[1])
            
            # Calcular rango de 3 meses
            three_months_start = f"{latest_year}-{max(1, latest_month - 2):02d}-01"
            period_end = f"{latest_period}-31"
            
            print(f"📅 Rango últimos 3 meses: {three_months_start} a {period_end}")
            
            # 2. Revenue últimos 3 meses
            cursor = conn.execute(f"""
                SELECT COUNT(*) as invoices, SUM(monto_total) as revenue
                FROM v_facturas_venta 
                WHERE fecha BETWEEN '{three_months_start}' AND '{period_end}'
            """)
            result = cursor.fetchone()
            invoices_3m, revenue_3m = result
            print(f"✅ Últimos 3 meses: {invoices_3m} facturas, ${revenue_3m:,.2f}")
            
            # 3. Revenue YTD
            cursor = conn.execute(f"""
                SELECT COUNT(*) as invoices, SUM(monto_total) as revenue
                FROM v_facturas_venta 
                WHERE strftime('%Y', fecha) = '{latest_year}'
            """)
            result = cursor.fetchone()
            invoices_ytd, revenue_ytd = result
            print(f"✅ YTD {latest_year}: {invoices_ytd} facturas, ${revenue_ytd:,.2f}")
            
        else:
            print("❌ No se encontró período con datos significativos")
        
        # 4. Debug proyectos
        print("\n4. Debug proyectos:")
        cursor = conn.execute("SELECT COUNT(*) FROM projects WHERE id IS NOT NULL")
        proj_direct = cursor.fetchone()[0]
        print(f"Proyectos en tabla 'projects': {proj_direct}")
        
        if proj_direct == 0:
            cursor = conn.execute("SELECT COUNT(*) FROM purchase_orders_unified")
            po_count = cursor.fetchone()[0]
            print(f"Purchase orders como proxy: {po_count}")
            
        # 5. Debug presupuestos
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM v_presupuesto_totales")
            budget_count = cursor.fetchone()[0]
            print(f"Presupuestos (PC): {budget_count}")
        except Exception as e:
            print(f"❌ Error presupuestos: {e}")
            
    except Exception as e:
        print(f"❌ Error general: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    debug_ceo_queries()