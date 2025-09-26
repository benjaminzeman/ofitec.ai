#!/usr/bin/env python3
"""Análisis de impacto de tablas vacías en funcionalidades"""

import sqlite3
from pathlib import Path

def analyze_empty_tables_impact():
    db_path = r"c:\Ofitec\ofitec.ai\data\chipax_data.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("⚠️  **ANÁLISIS DE IMPACTO - TABLAS VACÍAS CRÍTICAS**")
    print("=" * 60)
    
    # Tablas vacías que impactan funcionalidades
    empty_tables = {
        'customers': {
            'impacto': 'Alto - Impacta AR, facturación, reportes de clientes',
            'funcionalidades_afectadas': [
                'Dashboard de clientes',
                'Reportes de cuentas por cobrar',
                'Análisis de aging de clientes',
                'Facturas de venta sin datos de cliente'
            ],
            'datos_esperados': 'Información de clientes/razones sociales'
        },
        'vendors_unified': {
            'impacto': 'Alto - Impacta AP, compras, reportes de proveedores',
            'funcionalidades_afectadas': [
                'Dashboard de proveedores',
                'Reportes de cuentas por pagar',
                'Análisis de aging de proveedores',
                'Facturas de compra sin datos de proveedor'
            ],
            'datos_esperados': 'Información de proveedores/razones sociales'
        },
        'bank_accounts': {
            'impacto': 'Medio - Impacta configuración bancaria',
            'funcionalidades_afectadas': [
                'Configuración de cuentas bancarias',
                'Reconciliación bancaria automática',
                'Dashboard de caja'
            ],
            'datos_esperados': 'Configuración de cuentas bancarias'
        },
        'taxes': {
            'impacto': 'Medio - Impacta cálculos tributarios',
            'funcionalidades_afectadas': [
                'Cálculos de IVA',
                'Reportes tributarios',
                'Análisis de impuestos'
            ],
            'datos_esperados': 'Configuración de tipos de impuestos'
        }
    }
    
    for table, info in empty_tables.items():
        cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
        count = cursor.fetchone()[0]
        
        print(f"📋 **{table.upper()}** ({count} registros)")
        print(f"   Impacto: {info['impacto']}")
        print(f"   Funcionalidades afectadas:")
        for func in info['funcionalidades_afectadas']:
            print(f"     • {func}")
        print(f"   Datos esperados: {info['datos_esperados']}")
        print()
    
    conn.close()

if __name__ == "__main__":
    analyze_empty_tables_impact()