#!/usr/bin/env python3
import sqlite3

# Connect to the database
conn = sqlite3.connect('data/chipax_data.db')
cur = conn.cursor()

print('=== Debugging Simplified Revenue Logic ===')
print()

# Check if view exists
print('1. Checking if v_facturas_venta exists...')
cur.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='v_facturas_venta'")
view_exists = cur.fetchone() is not None
print(f'   View exists: {view_exists}')
print()

if view_exists:
    # Find best year by revenue 
    print('2. Finding best year by revenue...')
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
    print(f'   Best year row: {best_year_row}')
    print()
    
    if best_year_row:
        best_year, year_revenue = best_year_row
        print(f'3. Processing best year {best_year} with revenue {year_revenue}')
        
        # YTD = full year
        ytd = float(year_revenue or 0)
        print(f'   YTD: {ytd:,.2f}')
        
        # Check Q4 for monthly value
        print(f'4. Checking Q4 revenue for {best_year}...')
        cur.execute(f"""
            SELECT SUM(monto_total) FROM v_facturas_venta 
            WHERE strftime('%Y', fecha) = '{best_year}'
            AND strftime('%m', fecha) IN ('10', '11', '12')
        """)
        q4_result = cur.fetchone()
        print(f'   Q4 result: {q4_result}')
        
        # Calculate month value
        if q4_result and q4_result[0]:
            month = float(q4_result[0])
        else:
            month = ytd  # Fallback to full year
        
        print()
        print('=== FINAL RESULTS ===')
        print(f'Month: {month:,.2f}')
        print(f'YTD: {ytd:,.2f}')
    else:
        print('   No data found in best year query')
        month = ytd = 0.0
        print('   Setting month = ytd = 0.0')
else:
    print('   View does not exist - setting revenue to 0')
    month = ytd = 0.0

conn.close()
print()
print('=== Expected API Response ===')
print(f'"month": {{"real": {month}}}')
print(f'"ytd": {{"real": {ytd}}}')