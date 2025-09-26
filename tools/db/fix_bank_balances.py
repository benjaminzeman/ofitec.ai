#!/usr/bin/env python3
"""
Script para corregir los saldos bancarios acumulativos
"""
import sqlite3
from datetime import datetime

def calculate_running_balances():
    """Calcula saldos acumulativos para bank_movements"""
    conn = sqlite3.connect("data/chipax_data.db")
    try:
        print("=== CORRECCIÓN: Saldos Bancarios ===")
        
        # 1. Obtener todas las cuentas bancarias únicas
        cursor = conn.execute("""
            SELECT DISTINCT bank_name, account_number 
            FROM bank_movements 
            WHERE bank_name IS NOT NULL AND account_number IS NOT NULL
            ORDER BY bank_name, account_number
        """)
        accounts = cursor.fetchall()
        print(f"Procesando {len(accounts)} cuentas bancarias...")
        
        total_updated = 0
        
        for bank_name, account_number in accounts:
            print(f"\nProcesando: {bank_name} - {account_number}")
            
            # Obtener movimientos ordenados por fecha
            cursor = conn.execute("""
                SELECT id, monto, tipo
                FROM bank_movements 
                WHERE bank_name = ? AND account_number = ?
                ORDER BY fecha ASC, id ASC
            """, (bank_name, account_number))
            
            movements = cursor.fetchall()
            running_balance = 0.0
            updates = []
            
            for mov_id, monto, tipo in movements:
                # Aplicar monto según tipo
                if tipo and tipo.lower() in ['credito', 'credit', 'abono']:
                    running_balance += float(monto or 0)
                elif tipo and tipo.lower() in ['debito', 'debit', 'cargo']:
                    running_balance -= float(monto or 0)
                else:
                    # Si no hay tipo claro, usar el monto tal como está
                    running_balance += float(monto or 0)
                
                updates.append((running_balance, mov_id))
            
            # Actualizar saldos en batch
            conn.executemany(
                "UPDATE bank_movements SET saldo = ? WHERE id = ?",
                updates
            )
            total_updated += len(updates)
            print(f"  Actualizados {len(updates)} movimientos. Saldo final: ${running_balance:,.2f}")
        
        conn.commit()
        print(f"\n✅ Total registros actualizados: {total_updated}")
        
        # Verificar resultado
        cursor = conn.execute("SELECT COUNT(*) FROM bank_movements WHERE saldo != 0")
        non_zero_balances = cursor.fetchone()[0]
        print(f"✅ Registros con saldo != 0: {non_zero_balances}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    calculate_running_balances()