#!/usr/bin/env python3
"""
Test script for intelligent revenue period detection.
This validates the logic independently before deploying.
"""
import sqlite3


def _table_or_view_exists(conn: sqlite3.Connection, name: str) -> bool:
    """Check if a table or view exists in the database."""
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE (type='table' OR type='view') AND name=?", (name,)
    )
    return cur.fetchone() is not None


def _get_intelligent_revenue_period(conn: sqlite3.Connection) -> tuple[float, float]:
    """
    Get revenue for the most relevant period with significant business data.
    Returns (month_revenue, ytd_revenue) using intelligent period detection.
    """
    if not _table_or_view_exists(conn, "v_facturas_venta"):
        return 0.0, 0.0
        
    cur = conn.cursor()
    
    # Find year with highest revenue (most significant business period)
    cur.execute("""
        SELECT strftime('%Y', fecha) as year, 
               SUM(monto_total) as total_revenue,
               COUNT(*) as invoice_count
        FROM v_facturas_venta 
        WHERE fecha IS NOT NULL AND monto_total IS NOT NULL
        GROUP BY strftime('%Y', fecha)
        HAVING COUNT(*) >= 3  -- Require at least 3 invoices for significance
        ORDER BY total_revenue DESC
        LIMIT 1
    """)
    
    best_year_row = cur.fetchone()
    if not best_year_row:
        return 0.0, 0.0
        
    best_year, year_revenue, invoice_count = best_year_row
    ytd_revenue = float(year_revenue or 0)
    
    # Get Q4 revenue for monthly metric (most recent complete quarter)
    cur.execute("""
        SELECT SUM(monto_total) 
        FROM v_facturas_venta 
        WHERE strftime('%Y', fecha) = ? 
        AND strftime('%m', fecha) IN ('10', '11', '12')
        AND monto_total IS NOT NULL
    """, (best_year,))
    
    q4_result = cur.fetchone()
    month_revenue = float(q4_result[0] or 0) if q4_result and q4_result[0] else ytd_revenue
    
    return month_revenue, ytd_revenue


if __name__ == "__main__":
    print("=== Testing Intelligent Revenue Period Detection ===")
    
    # Connect to database
    conn = sqlite3.connect('data/chipax_data.db')
    
    print("\n1. Checking view existence...")
    view_exists = _table_or_view_exists(conn, "v_facturas_venta")
    print(f"   v_facturas_venta exists: {view_exists}")
    
    if view_exists:
        print("\n2. Running intelligent period detection...")
        month_revenue, ytd_revenue = _get_intelligent_revenue_period(conn)
        
        print(f"\n=== RESULTS ===")
        print(f"Month Revenue: ${month_revenue:,.2f}")
        print(f"YTD Revenue:   ${ytd_revenue:,.2f}")
        
        # Show the expected API response format
        print(f"\n=== Expected API Response ===")
        print(f'"month": {{"real": {round(month_revenue, 2)}}}')
        print(f'"ytd": {{"real": {round(ytd_revenue, 2)}}}')
        
        # Show additional context
        cur = conn.cursor()
        cur.execute("""
            SELECT strftime('%Y', fecha) as year, 
                   SUM(monto_total) as total_revenue,
                   COUNT(*) as invoice_count
            FROM v_facturas_venta 
            WHERE fecha IS NOT NULL AND monto_total IS NOT NULL
            GROUP BY strftime('%Y', fecha)
            HAVING COUNT(*) >= 3
            ORDER BY total_revenue DESC
            LIMIT 3
        """)
        
        print(f"\n=== Top 3 Revenue Years ===")
        for i, (year, revenue, count) in enumerate(cur.fetchall(), 1):
            print(f"{i}. {year}: ${revenue:,.2f} ({count} invoices)")
    else:
        print("   View not found - no revenue data available")
    
    conn.close()
    print("\n=== Test Complete ===")