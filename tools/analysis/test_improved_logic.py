#!/usr/bin/env python3
"""
Test de la lógica mejorada de períodos
"""
import sqlite3

def test_improved_logic():
    """Test de la lógica mejorada que prioriza volumen de revenue"""
    conn = sqlite3.connect("data/chipax_data.db")
    try:
        print("=== TEST: Lógica Mejorada ===")
        
        # 1. Buscar período con más volumen de datos
        cursor = conn.execute("""
            SELECT strftime('%Y-%m', fecha) as period,
                   COUNT(*) as invoice_count,
                   SUM(monto_total) as revenue
            FROM v_facturas_venta 
            WHERE fecha IS NOT NULL
            GROUP BY strftime('%Y-%m', fecha)
            HAVING COUNT(*) >= 3  -- Al menos 3 facturas
            ORDER BY strftime('%Y', fecha) DESC, revenue DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        
        if result:
            period, count, revenue = result
            print(f"✅ Mejor período encontrado: {period}")
            print(f"   📊 {count} facturas, ${revenue:,.2f}")
            
            year = period.split('-')[0]
            
            if count < 5:
                print(f"⚠️ Pocas facturas ({count}), usando todo el año {year}")
                cursor = conn.execute(f"""
                    SELECT COUNT(*) as total_invoices, SUM(monto_total) as year_revenue
                    FROM v_facturas_venta 
                    WHERE strftime('%Y', fecha) = '{year}'
                """)
                year_result = cursor.fetchone()
                if year_result:
                    total_inv, total_rev = year_result
                    print(f"✅ Año {year}: {total_inv} facturas, ${total_rev:,.2f}")
            else:
                print(f"✅ Suficientes facturas, usando últimos 3 meses desde {period}")
        
        # 2. Test fallback: año con mayor revenue
        print("\n2. Test fallback - Año con mayor revenue:")
        cursor = conn.execute("""
            SELECT strftime('%Y', fecha) as year, 
                   COUNT(*) as invoices,
                   SUM(monto_total) as revenue
            FROM v_facturas_venta 
            WHERE fecha IS NOT NULL
            GROUP BY strftime('%Y', fecha)
            ORDER BY revenue DESC
            LIMIT 3
        """)
        
        years = cursor.fetchall()
        for year, invoices, revenue in years:
            print(f"  {year}: {invoices} facturas, ${revenue:,.2f}")
            
        if years:
            best_year, best_invoices, best_revenue = years[0]
            print(f"\n🏆 Mejor año para fallback: {best_year} (${best_revenue:,.2f})")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_improved_logic()