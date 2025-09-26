"""
Migración para crear tablas del sistema de validaciones financieras.

Este script crea las tablas necesarias para almacenar:
- Reglas de validación
- Resultados de validaciones
- Flags de validación
- Centros de presupuesto
"""

import sqlite3
import os
from datetime import datetime

# Usar la misma ruta que el proyecto principal
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'ofitec_dev.db')

def run_migration():
    """Ejecutar migración para sistema de validaciones."""
    
    print(f"Ejecutando migración en: {DB_PATH}")
    
    # Verificar que la BD existe
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Base de datos no encontrada en {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # 1. Tabla para centros de presupuesto/costo
        print("Creando tabla budget_centers...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS budget_centers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cost_center TEXT NOT NULL UNIQUE,
                description TEXT,
                annual_budget REAL NOT NULL DEFAULT 0,
                period_budget REAL,
                manager_email TEXT,
                department TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Tabla para linking OCs con facturas AP
        print("Creando tabla ap_po_links...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ap_po_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                po_id TEXT NOT NULL,
                po_line_id TEXT,
                invoice_id TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (invoice_id) REFERENCES ap_invoices(id)
            )
        """)
        
        # 3. Tabla para pagos (si no existe)
        print("Creando tabla payments...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_number TEXT UNIQUE,
                invoice_id TEXT NOT NULL,
                amount REAL NOT NULL,
                payment_date DATE,
                payment_method TEXT,
                bank_reference TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (invoice_id) REFERENCES ap_invoices(id)
            )
        """)
        
        # 4. Tabla para líneas de órdenes de compra (si no existe)
        print("Creando tabla purchase_order_lines...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS purchase_order_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                po_number TEXT NOT NULL,
                line_number INTEGER NOT NULL,
                description TEXT,
                quantity REAL,
                unit_price REAL,
                line_total REAL NOT NULL,
                product_code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (po_number) REFERENCES purchase_orders_unified(po_number),
                UNIQUE(po_number, line_number)
            )
        """)
        
        # 5. Tabla para resultados de validaciones (log histórico)
        print("Creando tabla validation_results...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS validation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,  -- 'invoice', 'payment', 'po'
                entity_id TEXT NOT NULL,
                validation_type TEXT NOT NULL,  -- 'invoice_vs_po', 'payment_vs_invoice', etc.
                is_valid BOOLEAN NOT NULL,
                validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                validated_by TEXT,  -- usuario o 'system'
                validation_data TEXT  -- JSON con datos de la validación
            )
        """)
        
        # 6. Tabla para flags de validación (estado actual)
        print("Creando tabla validation_flags...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS validation_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                flag_type TEXT NOT NULL,
                severity TEXT NOT NULL,  -- 'error', 'warning', 'info'
                message TEXT NOT NULL,
                details TEXT,  -- JSON con detalles adicionales
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                resolved_by TEXT
            )
        """)
        
        # 7. Índices para optimizar consultas
        print("Creando índices...")
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_budget_centers_cost_center ON budget_centers(cost_center)",
            "CREATE INDEX IF NOT EXISTS idx_ap_po_links_po_id ON ap_po_links(po_id)",
            "CREATE INDEX IF NOT EXISTS idx_ap_po_links_invoice_id ON ap_po_links(invoice_id)",
            "CREATE INDEX IF NOT EXISTS idx_payments_invoice_id ON payments(invoice_id)",
            "CREATE INDEX IF NOT EXISTS idx_validation_results_entity ON validation_results(entity_type, entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_validation_flags_entity ON validation_flags(entity_type, entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_validation_flags_active ON validation_flags(is_active)"
        ]
        
        for idx_sql in indices:
            cur.execute(idx_sql)
        
        # 8. Insertar datos de ejemplo para testing
        print("Insertando datos de ejemplo...")
        
        # Centros de presupuesto de ejemplo
        cur.execute("""
            INSERT OR IGNORE INTO budget_centers (cost_center, description, annual_budget, department)
            VALUES 
                ('IT', 'Tecnología e Informática', 500000.0, 'Tecnología'),
                ('HR', 'Recursos Humanos', 200000.0, 'Administración'),
                ('OPS', 'Operaciones', 750000.0, 'Operaciones'),
                ('MKT', 'Marketing y Ventas', 300000.0, 'Comercial')
        """)
        
        # Algunas líneas de OC de ejemplo (si tenemos OCs)
        cur.execute("SELECT COUNT(*) as count FROM purchase_orders_unified LIMIT 1")
        if cur.fetchone()['count'] > 0:
            cur.execute("""
                INSERT OR IGNORE INTO purchase_order_lines (po_number, line_number, description, quantity, unit_price, line_total)
                SELECT 
                    po_number,
                    1,
                    'Línea principal - ' || description,
                    1,
                    total_amount,
                    total_amount
                FROM purchase_orders_unified 
                LIMIT 10
            """)
        
        # Commit cambios
        conn.commit()
        
        # Verificar que las tablas se crearon correctamente
        print("\nVerificando tablas creadas:")
        cur.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE '%budget%' OR name LIKE '%validation%' OR name LIKE '%payment%'
            ORDER BY name
        """)
        
        tables = cur.fetchall()
        for table in tables:
            print(f"  ✓ {table['name']}")
        
        print(f"\n✅ Migración completada exitosamente - {datetime.now()}")
        
        # Mostrar estadísticas
        cur.execute("SELECT COUNT(*) as count FROM budget_centers")
        budget_count = cur.fetchone()['count']
        print(f"   - Centros de presupuesto: {budget_count}")
        
        cur.execute("SELECT COUNT(*) as count FROM purchase_order_lines")
        lines_count = cur.fetchone()['count']  
        print(f"   - Líneas de OC: {lines_count}")
        
        return True
        
    except Exception as e:
        print(f"ERROR en migración: {str(e)}")
        return False
        
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)