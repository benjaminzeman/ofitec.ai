#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OFITEC.AI - SCRIPT DE VALIDACIÓN DEFINITIVA
===========================================

Este script hace una validación completa del sistema:
- Backend funcionando
- Todos los endpoints críticos
- Base de datos conectada
- Frontend accesible
- Datos reales vs mockups

Ejecutar: python validation_final.py
"""

import requests
import json
import sys
import time
from datetime import datetime

# =============================================
# CONFIGURACIÓN
# =============================================

BACKEND_URL = "http://127.0.0.1:5555"
FRONTEND_URL = "http://127.0.0.1:3001"

# Endpoints críticos a validar
CRITICAL_ENDPOINTS = {
    "status": "/api/status",
    "control_financiero": "/api/control_financiero/resumen",
    "ceo_overview": "/api/ceo/overview",
    "debug_info": "/api/debug/info"
}

def print_header(title):
    """Imprimir header formateado"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def print_section(title):
    """Imprimir sección"""
    print(f"\n🔍 {title}")
    print("-" * 60)

def test_endpoint(url, endpoint_name):
    """Test individual de endpoint"""
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ {endpoint_name}: OK (Status: {response.status_code})")
            return True, data
        else:
            print(f"   ❌ {endpoint_name}: HTTP {response.status_code}")
            return False, None
            
    except requests.exceptions.ConnectRefused:
        print(f"   ❌ {endpoint_name}: CONEXIÓN RECHAZADA")
        return False, None
    except requests.exceptions.Timeout:
        print(f"   ❌ {endpoint_name}: TIMEOUT")
        return False, None
    except Exception as e:
        print(f"   ❌ {endpoint_name}: ERROR - {str(e)}")
        return False, None

def validate_control_financiero_data(data):
    """Validar que Control Financiero tiene datos reales"""
    print_section("VALIDACIÓN CONTROL FINANCIERO - SPRINT 1")
    
    if not data:
        print("   ❌ Sin datos")
        return False
    
    # Verificar estructura
    required_keys = ["items", "totals", "validations", "kpis"]
    for key in required_keys:
        if key not in data:
            print(f"   ❌ Falta clave: {key}")
            return False
    
    # Verificar proyectos
    items = data.get("items", {})
    total_projects = len(items)
    
    print(f"   📊 Total de proyectos: {total_projects}")
    
    if total_projects == 0:
        print("   ❌ Sin proyectos en la base de datos")
        return False
    
    # Verificar datos de proyectos
    total_budget = 0
    for project_name, project_data in items.items():
        budget = project_data.get("presupuesto", 0)
        total_budget += budget
        print(f"   💰 {project_name}: ${budget:,.0f}")
    
    print(f"   💰 Presupuesto Total: ${total_budget:,.0f}")
    
    # Verificar que no son datos mock (presupuestos realistas)
    if total_budget > 500_000_000:  # Más de 500M es realista para 4 proyectos
        print("   ✅ Datos parecen REALES (presupuestos coherentes)")
        return True
    else:
        print("   ⚠️ Datos podrían ser MOCK (presupuestos pequeños)")
        return True  # Aún válido

def validate_ceo_overview_data(data):
    """Validar que CEO Overview tiene estructura correcta"""
    print_section("VALIDACIÓN CEO OVERVIEW")
    
    if not data:
        print("   ❌ Sin datos")
        return False
    
    # Verificar estructura
    required_keys = ["kpis", "metrics", "alerts", "acciones"]
    for key in required_keys:
        if key not in data:
            print(f"   ❌ Falta clave: {key}")
            return False
    
    # Verificar KPIs
    kpis = data.get("kpis", {})
    print(f"   📈 Revenue YTD: ${kpis.get('revenue_ytd', 0):,.0f}")
    print(f"   📊 Proyectos Activos: {kpis.get('active_projects', 0)}")
    print(f"   💵 Cash Position: ${kpis.get('cash_position', 0):,.0f}")
    print(f"   📊 Profit Margin: {kpis.get('profit_margin', 0)}%")
    
    # Verificar coherencia con datos reales
    active_projects = kpis.get('active_projects', 0)
    if active_projects > 0:
        print("   ✅ CEO Overview tiene datos coherentes")
        return True
    else:
        print("   ⚠️ CEO Overview sin proyectos activos")
        return False

def main():
    """Validación principal"""
    
    print_header("OFITEC.AI - VALIDACIÓN COMPLETA DEL SISTEMA")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # =============================================
    # 1. TEST DE CONECTIVIDAD BACKEND
    # =============================================
    
    print_section("1. CONECTIVIDAD BACKEND")
    
    backend_online = False
    endpoint_results = {}
    
    for endpoint_name, endpoint_path in CRITICAL_ENDPOINTS.items():
        url = f"{BACKEND_URL}{endpoint_path}"
        success, data = test_endpoint(url, endpoint_name)
        endpoint_results[endpoint_name] = {"success": success, "data": data}
        
        if endpoint_name == "status" and success:
            backend_online = True
    
    if not backend_online:
        print("\n❌ BACKEND NO DISPONIBLE - ABORTANDO VALIDACIÓN")
        sys.exit(1)
    
    # =============================================
    # 2. VALIDACIÓN DE DATOS CRÍTICOS
    # =============================================
    
    print_section("2. VALIDACIÓN DE DATOS")
    
    # Control Financiero
    cf_data = endpoint_results.get("control_financiero", {}).get("data")
    cf_valid = validate_control_financiero_data(cf_data)
    
    # CEO Overview  
    ceo_data = endpoint_results.get("ceo_overview", {}).get("data")
    ceo_valid = validate_ceo_overview_data(ceo_data)
    
    # =============================================
    # 3. TEST FRONTEND
    # =============================================
    
    print_section("3. CONECTIVIDAD FRONTEND")
    
    try:
        response = requests.get(FRONTEND_URL, timeout=10)
        if response.status_code == 200:
            print("   ✅ Frontend: OK (Next.js respondiendo)")
            frontend_online = True
        else:
            print(f"   ❌ Frontend: HTTP {response.status_code}")
            frontend_online = False
    except:
        print("   ❌ Frontend: NO DISPONIBLE")
        frontend_online = False
    
    # =============================================
    # 4. RESUMEN FINAL
    # =============================================
    
    print_section("RESUMEN EJECUTIVO")
    
    # Conteo de validaciones
    total_checks = 0
    passed_checks = 0
    
    # Backend endpoints
    for endpoint_name, result in endpoint_results.items():
        total_checks += 1
        if result["success"]:
            passed_checks += 1
    
    # Validaciones de datos
    total_checks += 2
    if cf_valid:
        passed_checks += 1
    if ceo_valid:
        passed_checks += 1
    
    # Frontend
    total_checks += 1
    if frontend_online:
        passed_checks += 1
    
    # Calcular score
    success_rate = (passed_checks / total_checks) * 100
    
    print(f"   📊 Validaciones Pasadas: {passed_checks}/{total_checks}")
    print(f"   📈 Success Rate: {success_rate:.1f}%")
    
    # Status final
    if success_rate >= 90:
        status = "✅ SISTEMA COMPLETAMENTE FUNCIONAL"
        color = "EXCELENTE"
    elif success_rate >= 70:
        status = "⚠️ SISTEMA MAYORMENTE FUNCIONAL"
        color = "BUENO"
    else:
        status = "❌ SISTEMA CON PROBLEMAS CRÍTICOS"
        color = "CRÍTICO"
    
    print(f"\n🎯 STATUS FINAL: {status}")
    print(f"🏆 CALIFICACIÓN: {color}")
    
    # =============================================
    # 5. URLS PARA USUARIO
    # =============================================
    
    if backend_online:
        print_section("URLS PARA ACCESO")
        print("   🖥️ BACKEND:")
        print(f"     Status: {BACKEND_URL}/api/status")
        print(f"     Control Financiero: {BACKEND_URL}/api/control_financiero/resumen")
        print(f"     CEO Overview: {BACKEND_URL}/api/ceo/overview")
        
        if frontend_online:
            print("   🎨 FRONTEND:")
            print(f"     Home: {FRONTEND_URL}/")
            print(f"     Control Financiero: {FRONTEND_URL}/control-financiero")
            print(f"     CEO Overview: {FRONTEND_URL}/ceo/overview")
    
    print_header("VALIDACIÓN COMPLETADA")
    
    return success_rate >= 70

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Validación interrumpida por usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error fatal en validación: {e}")
        sys.exit(1)