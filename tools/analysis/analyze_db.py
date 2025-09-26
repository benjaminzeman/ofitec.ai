#!/usr/bin/env python3
"""Análisis exhaustivo de la base de datos Ofitec.ai"""

import sqlite3
import json
from pathlib import Path

def analyze_database():
    db_path = r"c:\Ofitec\ofitec.ai\data\chipax_data.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("="*80)
    print("📊 ANÁLISIS EXHAUSTIVO DE LA BASE DE DATOS OFITEC.AI")
    print("="*80)
    print(f"Base de datos: {db_path}")
    print(f"Tamaño: {Path(db_path).stat().st_size / (1024*1024):.2f} MB")
    print()
    
    # Obtener todas las tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"📋 Total de tablas: {len(tables)}")
    print()
    
    # Análisis detallado por tabla
    table_analysis = {}
    total_records = 0
    
    for table_name in tables:
        try:
            # Contar registros
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            count = cursor.fetchone()[0]
            total_records += count
            
            # Obtener estructura de la tabla
            cursor.execute(f"PRAGMA table_info(`{table_name}`)")
            columns = cursor.fetchall()
            
            # Obtener sample de datos si hay registros
            sample_data = None
            if count > 0:
                cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 3")
                sample_data = cursor.fetchall()
            
            table_analysis[table_name] = {
                'count': count,
                'columns': columns,
                'sample': sample_data
            }
            
            # Status visual
            status = "✅" if count > 0 else "❌"
            print(f"{status} {table_name:<35} | {count:>8,} registros | {len(columns):>2} columnas")
            
        except Exception as e:
            print(f"❌ {table_name:<35} | ERROR: {e}")
    
    print()
    print(f"📊 **TOTAL DE REGISTROS EN LA BASE DE DATOS: {total_records:,}**")
    print()
    
    # Análisis de tablas críticas vacías
    empty_critical_tables = []
    critical_tables = [
        'bank_movements', 'sales_invoices', 'ap_invoices', 'expenses', 
        'ar_invoices', 'customers', 'vendors_unified', 'projects'
    ]
    
    print("🔍 **ANÁLISIS DE TABLAS CRÍTICAS:**")
    print("-" * 50)
    
    for table in critical_tables:
        if table in table_analysis:
            count = table_analysis[table]['count']
            if count == 0:
                empty_critical_tables.append(table)
                print(f"⚠️  {table}: VACÍA - Esto puede impactar funcionalidades")
            else:
                print(f"✅ {table}: {count:,} registros")
        else:
            print(f"❌ {table}: NO EXISTE")
    
    print()
    
    # Análisis de relaciones y consistencia
    print("🔗 **ANÁLISIS DE RELACIONES Y CONSISTENCIA:**")
    print("-" * 50)
    
    # Verificar reconciliaciones
    recon_count = table_analysis.get('recon_reconciliations', {}).get('count', 0)
    recon_links_count = table_analysis.get('recon_links', {}).get('count', 0)
    print(f"Reconciliaciones: {recon_count}")
    print(f"Links de reconciliación: {recon_links_count}")
    
    # Verificar facturas vs movimientos
    ap_count = table_analysis.get('ap_invoices', {}).get('count', 0)
    bank_count = table_analysis.get('bank_movements', {}).get('count', 0)
    print(f"Facturas AP: {ap_count:,}")
    print(f"Movimientos bancarios: {bank_count:,}")
    
    conn.close()
    
    return table_analysis, empty_critical_tables

if __name__ == "__main__":
    analyze_database()