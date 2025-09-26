#!/usr/bin/env python3
"""
Script para probar todos los links del proyecto Ofitec.ai
"""

import requests
import time
from urllib.parse import urljoin
import json
from datetime import datetime

# URLs base
FRONTEND_BASE = "http://localhost:3001"
BACKEND_BASE = "http://localhost:5555"

# Lista completa de rutas extraídas del Sidebar.tsx
FRONTEND_ROUTES = [
    # Dashboard principal
    "/",
    
    # Finanzas
    "/finanzas",
    "/finanzas/overview",
    "/finanzas/facturas-venta", 
    "/finanzas/facturas-compra",
    "/finanzas/gastos",
    "/finanzas/impuestos",
    "/finanzas/previred",
    "/finanzas/sueldos",
    "/finanzas/cartola-bancaria",
    "/ventas",
    "/finanzas/tesoreria",
    "/finanzas/ordenes-compra",
    "/finanzas/cashflow",
    "/finanzas/reportes-proyectos",
    "/finanzas/reportes-proveedores", 
    "/finanzas/conciliacion",
    "/finanzas/sii",
    "/finanzas/bancos",
    
    # Proyectos
    "/proyectos",
    "/proyectos/overview",
    "/proyectos/financiero",
    "/proyectos/subcontratistas",
    "/proyectos/cambios",
    "/proyectos/planning",
    
    # Operaciones  
    "/operaciones",
    "/operaciones/reportes",
    "/operaciones/hse", 
    "/operaciones/recursos",
    "/operaciones/comunicacion",
    
    # Documentos
    "/documentos",
    "/documentos/docuchat",
    "/documentos/rfi",
    "/documentos/biblioteca",
    
    # Riesgos
    "/riesgos",
    "/riesgos/matriz",
    "/riesgos/predicciones", 
    "/riesgos/alertas",
    
    # Portal Cliente
    "/cliente",
    "/cliente/proyecto",
    "/cliente/reportes",
    "/cliente/interaccion",
    
    # IA & Analytics
    "/ia",
    "/ia/copilots",
    "/ia/analytics",
    "/ia/insights",
    
    # Configuración
    "/config",
    "/config/usuarios",
    "/config/integraciones",
    "/config/personalizacion",
    
    # Rutas adicionales encontradas
    "/control-financiero",
    "/ceo/overview",
    "/proveedores",
]

# APIs del backend conocidas
BACKEND_APIS = [
    "/api/status",
    "/api/control_financiero/resumen", 
    "/api/ceo/overview",
    "/api/debug/info",
]

def test_url(url, timeout=10):
    """Probar una URL y retornar el estado"""
    try:
        response = requests.get(url, timeout=timeout)
        return {
            "url": url,
            "status_code": response.status_code,
            "status": "✅ OK" if response.status_code == 200 else f"⚠️ {response.status_code}",
            "response_time": round(response.elapsed.total_seconds() * 1000, 2),
            "content_length": len(response.content) if response.content else 0
        }
    except requests.exceptions.ConnectionError:
        return {
            "url": url,
            "status_code": None,
            "status": "❌ CONNECTION_ERROR",
            "response_time": None,
            "content_length": 0
        }
    except requests.exceptions.Timeout:
        return {
            "url": url, 
            "status_code": None,
            "status": "⏱️ TIMEOUT",
            "response_time": None,
            "content_length": 0
        }
    except Exception as e:
        return {
            "url": url,
            "status_code": None, 
            "status": f"❌ ERROR: {str(e)}",
            "response_time": None,
            "content_length": 0
        }

def main():
    print("🔍 REVISIÓN COMPLETA DE LINKS - OFITEC.AI")
    print("=" * 80)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {
        "frontend": [],
        "backend": [],
        "summary": {
            "total_tested": 0,
            "working": 0,
            "errors": 0,
            "warnings": 0
        }
    }
    
    # Probar rutas del frontend
    print("🌐 FRONTEND ROUTES (Next.js)")
    print("-" * 40)
    
    for route in FRONTEND_ROUTES:
        url = urljoin(FRONTEND_BASE, route)
        result = test_url(url)
        results["frontend"].append(result)
        results["summary"]["total_tested"] += 1
        
        if "✅" in result["status"]:
            results["summary"]["working"] += 1
        elif "⚠️" in result["status"]:
            results["summary"]["warnings"] += 1
        else:
            results["summary"]["errors"] += 1
            
        print(f"{result['status']} {route}")
        if result["response_time"]:
            print(f"    └─ {result['response_time']}ms, {result['content_length']} bytes")
        
        time.sleep(0.1)  # Pequeña pausa para no sobrecargar
    
    print()
    print("🔧 BACKEND APIs (Flask)")
    print("-" * 40)
    
    # Probar APIs del backend
    for api in BACKEND_APIS:
        url = urljoin(BACKEND_BASE, api)
        result = test_url(url)
        results["backend"].append(result)
        results["summary"]["total_tested"] += 1
        
        if "✅" in result["status"]:
            results["summary"]["working"] += 1
        elif "⚠️" in result["status"]:
            results["summary"]["warnings"] += 1
        else:
            results["summary"]["errors"] += 1
            
        print(f"{result['status']} {api}")
        if result["response_time"]:
            print(f"    └─ {result['response_time']}ms, {result['content_length']} bytes")
            
        time.sleep(0.1)
    
    # Resumen final
    print()
    print("📊 RESUMEN FINAL")
    print("=" * 40) 
    print(f"📄 Total URLs probadas: {results['summary']['total_tested']}")
    print(f"✅ Funcionando: {results['summary']['working']}")
    print(f"⚠️ Warnings: {results['summary']['warnings']}")
    print(f"❌ Errores: {results['summary']['errors']}")
    
    success_rate = (results['summary']['working'] / results['summary']['total_tested']) * 100
    print(f"📈 Tasa de éxito: {success_rate:.1f}%")
    
    # Guardar resultados en JSON
    with open('link_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Resultados guardados en: link_test_results.json")

if __name__ == "__main__":
    main()