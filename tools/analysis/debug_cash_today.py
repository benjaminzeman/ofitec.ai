#!/usr/bin/env python3
"""
Debug del cálculo de Cash Today
"""
import sqlite3

def main():
    conn = sqlite3.connect("data/chipax_data.db")
    try:
        print("=== DEBUG: Cash Today ===")
        
        # 1. Revisar estructura de bank_movements
        print("\n1. Campos disponibles en bank_movements:")
        cursor = conn.execute("PRAGMA table_info(bank_movements)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Columnas: {columns}")
        
        # 2. Ver si hay campo 'fecha' vs otros nombres
        print("\n2. Verificar datos de fechas:")
        cursor = conn.execute("SELECT fecha, COUNT(*) FROM bank_movements WHERE fecha IS NOT NULL GROUP BY fecha ORDER BY fecha DESC LIMIT 5")
        dates = cursor.fetchall()
        print(f"Fechas más recientes: {dates}")
        
        # 3. Ver si hay campo 'saldo'
        if 'saldo' in columns:
            print("\n3. Verificar saldos:")
            cursor = conn.execute("SELECT saldo, COUNT(*) FROM bank_movements WHERE saldo IS NOT NULL GROUP BY saldo ORDER BY saldo DESC LIMIT 10")
            saldos = cursor.fetchall()
            print(f"Saldos disponibles: {saldos}")
        else:
            print("\n3. ❌ NO HAY CAMPO 'saldo' en bank_movements")
        
        # 4. Ejecutar la consulta real del CEO endpoint
        print("\n4. Ejecutando consulta del CEO endpoint:")
        rows = conn.execute(
            "SELECT bank_name, account_number, MAX(date(fecha)) AS last_date FROM bank_movements GROUP BY bank_name, account_number"
        ).fetchall()
        print(f"Cuentas encontradas: {len(rows)}")
        
        cash_today = 0.0
        for bank_name, account_number, last_date in rows[:3]:  # Solo primeras 3
            print(f"\nProcesando: {bank_name} - {account_number} - {last_date}")
            if not last_date:
                print("  ❌ No hay fecha")
                continue
                
            cursor = conn.execute(
                """
                SELECT saldo FROM bank_movements
                 WHERE bank_name=? AND account_number=? AND date(fecha)=?
                 ORDER BY datetime(fecha) DESC, rowid DESC LIMIT 1
                """,
                (bank_name, account_number, last_date),
            )
            r = cursor.fetchone()
            if r and r[0] is not None:
                saldo = float(r[0] or 0)
                print(f"  ✅ Saldo encontrado: {saldo}")
                cash_today += saldo
            else:
                print(f"  ❌ No se encontró saldo para {last_date}")
        
        print(f"\n💰 CASH TODAY TOTAL: {cash_today}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()