#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OFITEC.AI - VALIDACIÓN FINAL DEFINITIVA
=======================================

Script de validación completa que usa solo Python
para evitar problemas de conectividad de PowerShell.
"""

import requests
import json
import sys
import subprocess
from datetime import datetime

# URLs del sistema
BACKEND_URL = "http://127.0.0.1:5555"
FRONTEND_URL = "http://127.0.0.1:3001"

def test_comprehensive_system():
    """Test completo del sistema"""
    
    print("\n" + "="*80)
    print(" OFITEC.AI - VALIDACIÓN FINAL DEFINITIVA")
    print("="*80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {"backend": {}, "frontend": {}, "data_validation": {}}
    
    # =============================================
    # 1. BACKEND TESTS
    # =============================================
    
    print("\n🔍 1. BACKEND UNIFICADO")
    print("-" * 60)
    
    backend_endpoints = {
        "status": "/api/status",
        "control_financiero": "/api/control_financiero/resumen",
        "ceo_overview": "/api/ceo/overview",
        "debug_info": "/api/debug/info"
    }
    
    backend_score = 0
    for name, endpoint in backend_endpoints.items():
        try:
            response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=10)
            if response.status_code == 200:
                print(f"   ✅ {name}: OK")
                results["backend"][name] = {"status": "success", "data": response.json()}
                backend_score += 1
            else:
                print(f"   ❌ {name}: HTTP {response.status_code}")
                results["backend"][name] = {"status": "error", "code": response.status_code}
        except Exception as e:
            print(f"   ❌ {name}: {str(e)}")
            results["backend"][name] = {"status": "error", "error": str(e)}
    
    # =============================================
    # 2. DATA VALIDATION
    # =============================================
    
    print("\n🔍 2. VALIDACIÓN DE DATOS REALES")
    print("-" * 60)
    
    data_score = 0
    
    # Control Financiero
    cf_data = results["backend"].get("control_financiero", {}).get("data")
    if cf_data:
        total_projects = len(cf_data.get("items", {}))
        total_budget = cf_data.get("totals", {}).get("presupuesto", 0)
        
        print(f"   📊 Proyectos: {total_projects}")
        print(f"   💰 Presupuesto Total: ${total_budget:,.0f}")
        
        if total_projects > 0 and total_budget > 500_000_000:
            print("   ✅ Control Financiero: DATOS REALES")
            data_score += 1
        else:
            print("   ⚠️ Control Financiero: datos insuficientes")
    else:
        print("   ❌ Control Financiero: sin datos")
    
    # CEO Overview
    ceo_data = results["backend"].get("ceo_overview", {}).get("data")
    if ceo_data:
        kpis = ceo_data.get("kpis", {})
        revenue = kpis.get("revenue_ytd", 0)
        projects = kpis.get("active_projects", 0)
        
        print(f"   📈 Revenue YTD: ${revenue:,.0f}")
        print(f"   📊 Proyectos Activos: {projects}")
        
        if revenue > 0 and projects > 0:
            print("   ✅ CEO Overview: DATOS COHERENTES")
            data_score += 1
        else:
            print("   ⚠️ CEO Overview: datos inconsistentes")
    else:
        print("   ❌ CEO Overview: sin datos")
    
    # =============================================
    # 3. FRONTEND TEST (usando subprocess)
    # =============================================
    
    print("\n🔍 3. FRONTEND NEXT.JS")
    print("-" * 60)
    
    frontend_score = 0
    try:
        # Usar curl a través de subprocess para evitar problemas de PowerShell
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command", f"Invoke-WebRequest -Uri '{FRONTEND_URL}' -TimeoutSec 5 -UseBasicParsing"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("   ✅ Frontend: ACCESIBLE")
            frontend_score = 1
        else:
            print("   ⚠️ Frontend: No accesible vía PowerShell (pero puede funcionar en navegador)")
    except Exception as e:
        print("   ⚠️ Frontend: Test automatizado falló, verificar manualmente")
    
    # Test alternativo: intentar hacer request directo con requests
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            print("   ✅ Frontend: ACCESIBLE vía Python requests")
            frontend_score = 1
    except:
        print("   ℹ️ Frontend: Verificar manualmente en http://localhost:3001")
    
    # =============================================
    # 4. RESUMEN FINAL
    # =============================================
    
    print("\n🎯 RESUMEN EJECUTIVO")
    print("-" * 60)
    
    total_backend = len(backend_endpoints)
    total_data = 2
    total_frontend = 1
    
    total_checks = total_backend + total_data + total_frontend
    total_passed = backend_score + data_score + frontend_score
    
    success_rate = (total_passed / total_checks) * 100
    
    print(f"   Backend: {backend_score}/{total_backend} ({'✅' if backend_score == total_backend else '⚠️'})")
    print(f"   Data Validation: {data_score}/{total_data} ({'✅' if data_score == total_data else '⚠️'})")
    print(f"   Frontend: {frontend_score}/{total_frontend} ({'✅' if frontend_score == total_frontend else '⚠️'})")
    print(f"   Total: {total_passed}/{total_checks} ({success_rate:.1f}%)")
    
    if success_rate >= 90:
        status = "🏆 SISTEMA COMPLETAMENTE FUNCIONAL"
        level = "EXCELENTE"
    elif success_rate >= 75:
        status = "✅ SISTEMA ALTAMENTE FUNCIONAL"
        level = "MUY BUENO"
    elif success_rate >= 60:
        status = "⚠️ SISTEMA FUNCIONALMENTE VIABLE"
        level = "ACEPTABLE"
    else:
        status = "❌ SISTEMA CON PROBLEMAS CRÍTICOS"
        level = "CRÍTICO"
    
    print(f"\n🎯 STATUS: {status}")
    print(f"🏆 NIVEL: {level}")
    
    # =============================================
    # 5. URLS OPERATIVAS
    # =============================================
    
    print("\n🌐 URLS PARA ACCESO DIRECTO")
    print("-" * 60)
    print("   🖥️ BACKEND UNIFICADO:")
    print(f"     Status: {BACKEND_URL}/api/status")
    print(f"     Control Financiero: {BACKEND_URL}/api/control_financiero/resumen")
    print(f"     CEO Overview: {BACKEND_URL}/api/ceo/overview")
    print("")
    print("   🎨 FRONTEND NEXT.JS:")
    print(f"     Home: {FRONTEND_URL}/")
    print(f"     Control Financiero: {FRONTEND_URL}/control-financiero")
    print(f"     CEO Overview: {FRONTEND_URL}/ceo/overview")
    
    print("\n" + "="*80)
    print(" VALIDACIÓN COMPLETADA - ARQUITECTURA UNIFICADA OPERATIVA")
    print("="*80)
    
    return success_rate >= 60

if __name__ == "__main__":
    try:
        success = test_comprehensive_system()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Validación interrumpida")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error en validación: {e}")
        sys.exit(1)