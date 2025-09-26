#!/usr/bin/env python3
"""
Diseño de lógica inteligente para períodos de dashboard CEO
"""
import sqlite3
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

def get_intelligent_periods():
    """
    Determina los períodos más relevantes para el dashboard CEO
    usando lógica adaptativa basada en disponibilidad de datos
    """
    conn = sqlite3.connect("data/chipax_data.db")
    try:
        print("=== ANÁLISIS: Períodos Inteligentes para CEO ===")
        
        # 1. Encontrar el último mes con datos significativos
        cursor = conn.execute("""
            SELECT 
                strftime('%Y-%m', fecha) as period,
                COUNT(*) as invoice_count,
                SUM(monto_total) as revenue,
                MAX(fecha) as latest_date
            FROM v_facturas_venta 
            WHERE fecha IS NOT NULL
            GROUP BY strftime('%Y-%m', fecha)
            HAVING COUNT(*) >= 3  -- Al menos 3 facturas para ser significativo
            ORDER BY period DESC
            LIMIT 12  -- Últimos 12 meses con datos
        """)
        
        periods_data = cursor.fetchall()
        
        if not periods_data:
            print("❌ No hay datos suficientes")
            return None
            
        print("Períodos con datos significativos:")
        for period, count, revenue, latest in periods_data:
            print(f"  {period}: {count} facturas, ${revenue:,.0f}")
        
        # 2. Definir períodos inteligentes
        latest_period = periods_data[0][0]  # Último período con datos
        print(f"\n🎯 Último período con datos significativos: {latest_period}")
        
        # Calcular períodos dinámicos
        latest_date = datetime.strptime(latest_period + "-01", "%Y-%m-%d")
        
        periods = {
            "current_month": {
                "start": latest_date.strftime("%Y-%m-01"),
                "end": (latest_date + relativedelta(months=1) - timedelta(days=1)).strftime("%Y-%m-%d"),
                "label": f"Mes Actual ({latest_date.strftime('%b %Y')})"
            },
            "last_3_months": {
                "start": (latest_date - relativedelta(months=2)).strftime("%Y-%m-01"),
                "end": (latest_date + relativedelta(months=1) - timedelta(days=1)).strftime("%Y-%m-%d"),
                "label": "Últimos 3 Meses"
            },
            "ytd": {
                "start": latest_date.strftime("%Y-01-01"),
                "end": (latest_date + relativedelta(months=1) - timedelta(days=1)).strftime("%Y-%m-%d"),
                "label": f"YTD {latest_date.year}"
            },
            "last_12_months": {
                "start": (latest_date - relativedelta(months=11)).strftime("%Y-%m-01"),
                "end": (latest_date + relativedelta(months=1) - timedelta(days=1)).strftime("%Y-%m-%d"),
                "label": "Rolling 12 Meses"
            },
            "previous_year": {
                "start": f"{latest_date.year - 1}-01-01",
                "end": f"{latest_date.year - 1}-12-31", 
                "label": f"Año {latest_date.year - 1}"
            }
        }
        
        print("\n📊 Períodos calculados dinámicamente:")
        for key, period in periods.items():
            print(f"  {key}: {period['start']} a {period['end']} ({period['label']})")
        
        return periods, latest_period
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None
    finally:
        conn.close()


def test_dynamic_queries():
    """Prueba consultas con períodos dinámicos"""
    periods, latest_period = get_intelligent_periods()
    if not periods:
        return
        
    conn = sqlite3.connect("data/chipax_data.db")
    try:
        print("\n=== PRUEBA: Consultas Dinámicas ===")
        
        for period_key, period_info in periods.items():
            cursor = conn.execute(f"""
                SELECT 
                    COUNT(*) as invoices,
                    SUM(monto_total) as revenue
                FROM v_facturas_venta 
                WHERE fecha BETWEEN '{period_info['start']}' AND '{period_info['end']}'
            """)
            
            result = cursor.fetchone()
            invoices, revenue = result if result else (0, 0)
            
            print(f"  {period_info['label']}: {invoices} facturas, ${revenue:,.0f}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    get_intelligent_periods()
    test_dynamic_queries()