#!/usr/bin/env python3
"""
Script de análisis completo del sistema de conciliación actual.
Entiende qué tenemos para luego mejorarlo.
"""

import sqlite3
import json
import os
from datetime import datetime
import sys

def analyze_database():
    """Analizar la estructura completa de la base de datos"""
    print("🔍 ANÁLISIS COMPLETO DEL SISTEMA DE CONCILIACIÓN")
    print("=" * 60)
    
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'chipax_data.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Listar todas las tablas
    print("\n📊 1. TABLAS EN LA BASE DE DATOS:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    movement_tables = []
    document_tables = []
    recon_tables = []
    other_tables = []
    
    for table in sorted(tables):
        if 'movement' in table.lower() or 'cartola' in table.lower() or 'bank' in table.lower():
            movement_tables.append(table)
        elif 'document' in table.lower() or 'invoice' in table.lower() or 'factura' in table.lower():
            document_tables.append(table)
        elif 'recon' in table.lower() or 'concilia' in table.lower():
            recon_tables.append(table)
        else:
            other_tables.append(table)
    
    print("   🏦 Movimientos bancarios:", movement_tables or "No encontradas")
    print("   📄 Documentos:", document_tables or "No encontradas")
    print("   🔗 Reconciliación:", recon_tables or "No encontradas")
    print("   📋 Otras:", len(other_tables), "tablas")
    
    # 2. Analizar tablas de reconciliación
    print("\n🔗 2. ANÁLISIS DE TABLAS DE RECONCILIACIÓN:")
    for table in recon_tables:
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            
            print(f"\n   📋 Tabla: {table} ({count} registros)")
            for col in columns:
                print(f"      • {col[1]}: {col[2]}")
                
            # Mostrar algunos registros de ejemplo
            if count > 0:
                cursor.execute(f"SELECT * FROM {table} LIMIT 3")
                rows = cursor.fetchall()
                print(f"      📝 Primeros registros:")
                for i, row in enumerate(rows, 1):
                    print(f"         {i}: {dict(zip([col[1] for col in columns], row))}")
        except Exception as e:
            print(f"   ❌ Error analizando {table}: {e}")
    
    # 3. Buscar tablas que podrían contener movimientos
    print("\n🏦 3. BUSCANDO DATOS DE MOVIMIENTOS:")
    potential_movement_tables = []
    for table in tables:
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1].lower() for col in cursor.fetchall()]
            
            # Buscar columnas típicas de movimientos bancarios
            movement_indicators = ['amount', 'monto', 'date', 'fecha', 'description', 'descripcion', 'gloss']
            if any(indicator in ' '.join(columns) for indicator in movement_indicators):
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                if count > 0:
                    potential_movement_tables.append((table, count, columns))
        except:
            continue
    
    print("   📊 Tablas con datos de movimientos potenciales:")
    for table, count, columns in potential_movement_tables:
        print(f"      • {table}: {count} registros")
        print(f"        Columnas: {', '.join(columns[:10])}{'...' if len(columns) > 10 else ''}")
    
    # 4. Analizar configuración de IA
    print("\n🤖 4. CONFIGURACIÓN DE IA:")
    ai_config_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'ai_config.json')
    if os.path.exists(ai_config_path):
        with open(ai_config_path, 'r', encoding='utf-8') as f:
            ai_config = json.load(f)
        print("   ✅ Configuración de IA encontrada:")
        for key, value in ai_config.items():
            if isinstance(value, dict):
                print(f"      • {key}: {len(value)} elementos")
            else:
                print(f"      • {key}: {value}")
    else:
        print("   ❌ No se encontró configuración de IA")
    
    # 5. Analizar patrones extraídos
    print("\n📊 5. PATRONES EXTRAÍDOS:")
    patterns_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'conciliation_patterns.json')
    if os.path.exists(patterns_path):
        with open(patterns_path, 'r', encoding='utf-8') as f:
            patterns = json.load(f)
        print("   ✅ Patrones encontrados:")
        print(f"      • Archivos procesados: {patterns.get('files_processed', 0)}")
        print(f"      • Total conciliaciones: {patterns.get('total_reconciliations', 0)}")
        print(f"      • Aliases de proveedores: {len(patterns.get('vendor_aliases', {}))}")
        print(f"      • Patrones de timing: {len(patterns.get('timing_patterns', {}))}")
        print(f"      • Tolerancias de monto: {len(patterns.get('amount_tolerances', {}))}")
        
        # Mostrar categorías
        if 'category_stats' in patterns:
            print("   📋 Categorías analizadas:")
            for cat, stats in patterns['category_stats'].items():
                print(f"      • {cat}: {stats.get('count', 0)} conciliaciones")
    else:
        print("   ❌ No se encontraron patrones extraídos")
    
    conn.close()
    return potential_movement_tables, recon_tables

def analyze_api_endpoints():
    """Analizar los endpoints de la API"""
    print("\n🌐 6. ENDPOINTS DE API DISPONIBLES:")
    
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
        import server
        
        app = server.app
        conciliation_routes = []
        other_routes = []
        
        for rule in app.url_map.iter_rules():
            route_info = f"{list(rule.methods)} {rule.rule}"
            if 'conciliacion' in rule.rule:
                conciliation_routes.append(route_info)
            else:
                other_routes.append(route_info)
        
        print("   🔗 Endpoints de conciliación:")
        for route in conciliation_routes:
            print(f"      • {route}")
        
        print(f"\n   📋 Total de otros endpoints: {len(other_routes)}")
        
    except Exception as e:
        print(f"   ❌ Error analizando API: {e}")

def analyze_reconcile_engine():
    """Analizar el motor de reconciliación"""
    print("\n⚙️ 7. MOTOR DE RECONCILIACIÓN:")
    
    engine_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'reconcile_engine.py')
    if os.path.exists(engine_path):
        print("   ✅ Motor de reconciliación encontrado")
        
        # Analizar funciones principales
        with open(engine_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        functions = []
        for line in content.split('\n'):
            if line.startswith('def '):
                func_name = line.split('(')[0].replace('def ', '')
                functions.append(func_name)
        
        print(f"   🔧 Funciones disponibles ({len(functions)}):")
        for func in functions[:10]:  # Mostrar primeras 10
            print(f"      • {func}")
        if len(functions) > 10:
            print(f"      • ... y {len(functions) - 10} más")
    else:
        print("   ❌ Motor de reconciliación no encontrado")

def generate_recommendations():
    """Generar recomendaciones de mejora"""
    print("\n💡 8. RECOMENDACIONES DE MEJORA:")
    print("   🎯 Basado en el análisis, se recomienda:")
    print("      1. Crear datos de prueba para movimientos y documentos")
    print("      2. Implementar interface de testing para la IA")
    print("      3. Crear endpoint de conciliación con datos sintéticos")
    print("      4. Validar que los 37,382 patrones se estén usando correctamente")
    print("      5. Implementar métricas de rendimiento de la IA")

def main():
    """Función principal de análisis"""
    try:
        movement_tables, recon_tables = analyze_database()
        analyze_api_endpoints()
        analyze_reconcile_engine()
        generate_recommendations()
        
        print("\n✨ ANÁLISIS COMPLETADO")
        print("   📊 Sistema analizado completamente")
        print("   🚀 Listo para implementar mejoras")
        
        return movement_tables, recon_tables
        
    except Exception as e:
        print(f"\n❌ Error durante el análisis: {e}")
        import traceback
        traceback.print_exc()
        return [], []

if __name__ == "__main__":
    main()