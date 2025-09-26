#!/usr/bin/env python3
import sqlite3

# Connect and check
conn = sqlite3.connect('data/chipax_data.db')
cur = conn.cursor()

print("1. Checking view existence...")
cur.execute("SELECT name FROM sqlite_master WHERE name='v_facturas_venta'")
view_check = cur.fetchone()
print(f"View check result: {view_check}")

if view_check:
    print("\n2. Finding best year...")
    cur.execute("""
        SELECT strftime('%Y', fecha) as year, 
               SUM(monto_total) as revenue
        FROM v_facturas_venta 
        WHERE fecha IS NOT NULL
        GROUP BY strftime('%Y', fecha)
        ORDER BY revenue DESC
        LIMIT 1
    """)
    best_year_row = cur.fetchone()
    print(f"Best year row: {best_year_row}")
    
    if best_year_row:
        best_year, year_revenue = best_year_row
        ytd = float(year_revenue or 0)
        print(f"YTD: {ytd:,.2f}")
        
        print(f"\n3. Getting Q4 for {best_year}...")
        cur.execute(f"""
            SELECT SUM(monto_total) FROM v_facturas_venta 
            WHERE strftime('%Y', fecha) = '{best_year}'
            AND strftime('%m', fecha) IN ('10', '11', '12')
        """)
        q4_result = cur.fetchone()
        print(f"Q4 result: {q4_result}")
        
        if q4_result and q4_result[0]:
            month = float(q4_result[0])
        else:
            month = ytd
        print(f"Month: {month:,.2f}")
    else:
        print("No best year found")

conn.close()