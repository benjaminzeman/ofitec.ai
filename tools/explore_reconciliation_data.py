#!/usr/bin/env python3
"""
Explorador de Datos para Conciliación Bancaria
Muestra la relación correcta: Movimiento Bancario ←→ Documento de Respaldo
"""

import sqlite3
import os

def explore_bank_reconciliation_data():
    """Explorar datos reales para conciliación bancaria"""
    print("🏦 EXPLORADOR DE CONCILIACIÓN BANCARIA")
    print("=" * 50)
    
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'chipax_data.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Movimientos bancarios de ejemplo
    print("\n1️⃣ MOVIMIENTOS BANCARIOS (Dinero que entra/sale):")
    cursor.execute("""
        SELECT id, fecha, glosa, monto, tipo 
        FROM bank_movements 
        WHERE monto IS NOT NULL 
        ORDER BY RANDOM() 
        LIMIT 5
    """)
    
    movements = cursor.fetchall()
    for mov in movements:
        direction = "💰 ENTRADA" if mov['monto'] > 0 else "💸 SALIDA "
        print(f"   {mov['id']:5d} | {direction} | ${mov['monto']:>12,.0f} | {mov['glosa'][:60]}")
    
    # 2. Documentos de respaldo disponibles
    print("\n2️⃣ DOCUMENTOS DE RESPALDO DISPONIBLES:")
    
    # Facturas de Compra (para pagos que hacemos)
    cursor.execute("SELECT COUNT(*) as count FROM ap_invoices")
    ap_count = cursor.fetchone()['count']
    print(f"   📄 Facturas de Compra: {ap_count:,} documentos")
    
    # Facturas de Venta (para pagos que recibimos)  
    cursor.execute("SELECT COUNT(*) as count FROM sales_invoices")
    sales_count = cursor.fetchone()['count']
    print(f"   📄 Facturas de Venta: {sales_count:,} documentos")
    
    # Gastos
    cursor.execute("SELECT COUNT(*) as count FROM expenses")
    expense_count = cursor.fetchone()['count']
    print(f"   💰 Gastos: {expense_count:,} documentos")
    
    # Impuestos
    cursor.execute("SELECT COUNT(*) as count FROM taxes")
    tax_count = cursor.fetchone()['count']
    print(f"   🏛️ Impuestos: {tax_count:,} documentos")
    
    # 3. Ejemplos de conciliaciones ya hechas
    print("\n3️⃣ CONCILIACIONES EXISTENTES (Ejemplos de la lógica correcta):")
    cursor.execute("""
        SELECT rl.*, bm.glosa, bm.monto as mov_monto
        FROM recon_links rl
        JOIN bank_movements bm ON rl.bank_movement_id = bm.id
        LIMIT 3
    """)
    
    existing_recons = cursor.fetchall()
    for recon in existing_recons:
        print(f"\n   🔗 Conciliación ID {recon['id']}:")
        print(f"      🏦 Movimiento: ${recon['mov_monto']:,.0f} - {recon['glosa'][:50]}")
        
        docs = []
        if recon['sales_invoice_id']:
            docs.append(f"Factura Venta #{recon['sales_invoice_id']}")
        if recon['purchase_invoice_id']:
            docs.append(f"Factura Compra #{recon['purchase_invoice_id']}")
        if recon['expense_id']:
            docs.append(f"Gasto #{recon['expense_id']}")
        if recon['payroll_id']:
            docs.append(f"Sueldo #{recon['payroll_id']}")
        if recon['tax_id']:
            docs.append(f"Impuesto #{recon['tax_id']}")
            
        print(f"      📄 Documentos: {', '.join(docs) if docs else 'Ninguno específico'}")
        print(f"      💰 Monto conciliado: ${recon['amount']:,.0f}")
    
    # 4. Buscar un ejemplo perfecto para demostrar
    print("\n4️⃣ BUSCANDO EJEMPLO PERFECTO PARA DEMO:")
    
    # Buscar movimiento bancario negativo (pago) que podamos conciliar
    cursor.execute("""
        SELECT id, fecha, glosa, monto 
        FROM bank_movements 
        WHERE monto < 0 
        AND ABS(monto) BETWEEN 50000 AND 1000000
        AND glosa IS NOT NULL 
        AND LENGTH(glosa) > 10
        ORDER BY RANDOM() 
        LIMIT 3
    """)
    
    demo_movements = cursor.fetchall()
    print("   🎯 Movimientos candidatos para demo (pagos):")
    
    for mov in demo_movements:
        print(f"      {mov['id']:5d} | ${mov['monto']:>10,.0f} | {mov['glosa']}")
        
        # Buscar facturas de compra con monto similar
        amount_range = abs(mov['monto']) * 0.05  # 5% tolerancia
        cursor.execute("""
            SELECT id, vendor_name, total_amount, invoice_number
            FROM ap_invoices 
            WHERE ABS(total_amount - ?) < ?
            LIMIT 2
        """, (abs(mov['monto']), amount_range))
        
        matching_invoices = cursor.fetchall()
        if matching_invoices:
            print(f"         💡 Posibles facturas coincidentes:")
            for inv in matching_invoices:
                print(f"            F#{inv['id']} | {inv['vendor_name'][:30]} | ${inv['total_amount']:,.0f}")
    
    conn.close()
    
    print("\n✨ LÓGICA DE CONCILIACIÓN BANCARIA:")
    print("   🏦 Movimiento Bancario (entrada/salida de dinero)")
    print("   ↕️")
    print("   📄 Documento de Respaldo (factura, gasto, impuesto, etc.)")
    print("   ✅ = CONCILIADO (sabemos de dónde viene/a dónde va el dinero)")

if __name__ == "__main__":
    explore_bank_reconciliation_data()