#!/usr/bin/env python3
import sqlite3
import sys

# Connect to database
conn = sqlite3.connect('data/chipax_data.db')
cur = conn.cursor()

print("=== FINAL DEBUG TEST ===")

# Test 1: View exists?
print("\n1. Testing view existence...")
cur.execute("SELECT name FROM sqlite_master WHERE name='v_facturas_venta'")
view_result = cur.fetchone()
print(f"View check: {view_result}")

if view_result:
    print("\n2. Testing best year query...")
    cur.execute("SELECT strftime('%Y', fecha) as year, SUM(monto_total) as revenue FROM v_facturas_venta WHERE fecha IS NOT NULL GROUP BY strftime('%Y', fecha) ORDER BY revenue DESC LIMIT 1")
    best_year_result = cur.fetchone()
    print(f"Best year result: {best_year_result}")
    
    if best_year_result:
        best_year, year_revenue = best_year_result
        ytd = float(year_revenue or 0)
        print(f"YTD calculated: {ytd}")
        
        print(f"\n3. Testing Q4 query for year {best_year}...")
        cur.execute(f"SELECT SUM(monto_total) FROM v_facturas_venta WHERE strftime('%Y', fecha) = '{best_year}' AND strftime('%m', fecha) IN ('10', '11', '12')")
        q4_result = cur.fetchone()
        print(f"Q4 result: {q4_result}")
        
        month = float(q4_result[0] or 0) if q4_result and q4_result[0] else ytd
        print(f"Month calculated: {month}")
        
        print(f"\n=== FINAL VALUES ===")
        print(f"Month: {month:,.2f}")
        print(f"YTD: {ytd:,.2f}")
    else:
        print("No best year result found")
else:
    print("View does not exist")

conn.close()