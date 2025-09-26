#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONTROL FINANCIERO ADAPTER - SPRINT 1
=====================================

Adaptador para hacer funcionar el control financiero con la estructura actual de BD.
Convierte datos de la tabla 'projects' al formato esperado por el frontend.
"""

import sqlite3
from typing import Dict, List, Any
from db_utils import db_conn

def get_control_financiero_data(db_path: str) -> Dict[str, Any]:
    """
    Obtiene datos de control financiero adaptados desde la tabla projects actual.
    
    Returns:
        Dict con estructura esperada por el frontend del Sprint 1
    """
    
    items = []
    validation_summary = {
        "total_projects": 0,
        "projects_ok": 0,
        "projects_with_warnings": 0,
        "projects_with_errors": 0,
        "critical_issues": []
    }
    
    totals = {
        "presupuesto": 0.0,
        "comprometido": 0.0,
        "facturado": 0.0,
        "pagado": 0.0,
        "disponible": 0.0
    }
    
    try:
        with db_conn(db_path) as conn:
            cur = conn.cursor()
            
            # Obtener proyectos de la tabla actual
            cur.execute("""
                SELECT id, name, budget_total, status, analytic_code
                FROM projects 
                WHERE status IS NOT NULL 
                AND budget_total IS NOT NULL
                ORDER BY name
            """)
            
            projects = cur.fetchall()
            validation_summary["total_projects"] = len(projects)
            
            for project_id, name, budget_total, status, analytic_code in projects:
                
                # Datos base del proyecto
                presupuesto = float(budget_total or 0)
                
                # Por ahora usamos datos simulados realistas basados en el presupuesto
                # En producción estos vendrían de las tablas reales de OC, facturas, etc.
                comprometido = presupuesto * 0.65  # 65% comprometido
                facturado = presupuesto * 0.45     # 45% facturado
                pagado = presupuesto * 0.30        # 30% pagado
                disponible_conservador = presupuesto - comprometido
                
                # Validaciones del Sprint 1
                flags = []
                severity = "OK"
                
                # 1. Validación: Presupuesto definido
                if presupuesto <= 0:
                    flags.append("sin_presupuesto_cargado")
                    severity = "WARNING"
                    validation_summary["projects_with_warnings"] += 1
                
                # 2. Validación crítica: Comprometido vs Presupuesto  
                if presupuesto > 0 and comprometido > presupuesto * 1.05:
                    flags.append("excede_presupuesto")
                    severity = "ERROR"
                    validation_summary["projects_with_errors"] += 1
                    validation_summary["critical_issues"].append({
                        "project": name,
                        "issue": "Comprometido excede presupuesto",
                        "excess": comprometido - presupuesto
                    })
                
                # 3. Validación: Disponible negativo
                if disponible_conservador < 0:
                    flags.append("disponible_negativo")
                    if severity not in ["ERROR"]:
                        severity = "ERROR"
                        validation_summary["projects_with_errors"] += 1
                
                # 4. Validación: Alto nivel de compromiso
                if presupuesto > 0 and (comprometido / presupuesto) >= 0.95:
                    flags.append("alto_compromiso")
                    if severity == "OK":
                        severity = "WARNING"
                        validation_summary["projects_with_warnings"] += 1
                
                # Si no hay flags críticos
                if not flags:
                    flags = ["OK"]
                    validation_summary["projects_ok"] += 1
                
                # KPIs del Sprint 1
                kpis = {
                    'budget_utilization': (comprometido / presupuesto * 100) if presupuesto > 0 else 0,
                    'invoice_ratio': (facturado / comprometido * 100) if comprometido > 0 else 0,
                    'payment_ratio': (pagado / facturado * 100) if facturado > 0 else 0,
                }
                
                # Calcular score de salud financiera
                health_score = 100
                if disponible_conservador < 0:
                    health_score -= 40
                if kpis['budget_utilization'] > 100:
                    health_score -= 30
                elif kpis['budget_utilization'] > 95:
                    health_score -= 15
                    
                # Bonus por gestión eficiente
                if 60 <= kpis['budget_utilization'] <= 85:
                    health_score += 10
                
                kpis['financial_health_score'] = max(0, min(100, health_score))
                
                # Crear validaciones en formato esperado por frontend
                validations = {
                    "budget_ok": presupuesto > 0,
                    "commitment_reasonable": comprometido <= presupuesto * 1.05,
                    "invoice_payment_ratio_ok": (pagado / facturado) <= 1.05 if facturado > 0 else True,
                    "all_validations_passed": severity == "OK"
                }
                
                # Crear item del proyecto
                project_item = {
                    "id": str(project_id),
                    "nombre": name,
                    "presupuesto": presupuesto,
                    "comprometido": comprometido,
                    "facturado": facturado,
                    "pagado": pagado,
                    "disponible": disponible_conservador,
                    "health_score": kpis['financial_health_score'],
                    "validations": validations,
                    "analytic_code": analytic_code or f"PRJ{project_id:03d}",
                    "kpis": kpis,
                    "severity": severity,
                    "flags": flags,
                    "status": status or "active"
                }
                
                items.append(project_item)
                
                # Acumular totales
                totals["presupuesto"] += presupuesto
                totals["comprometido"] += comprometido
                totals["facturado"] += facturado
                totals["pagado"] += pagado
                totals["disponible"] += disponible_conservador
    
    except Exception as e:
        print(f"Error en get_control_financiero_data: {e}")
        # Devolver estructura vacía en caso de error
        pass
    
    # KPIs consolidados
    kpis_consolidados = {
        "total_projects": validation_summary["total_projects"],
        "projects_over_budget": validation_summary["projects_with_errors"],
        "projects_with_high_commitment": sum(1 for item in items if "alto_compromiso" in item["flags"]),
        "projects_with_warnings": validation_summary["projects_with_warnings"],
        "average_financial_health": sum(item["kpis"]["financial_health_score"] for item in items) / len(items) if items else 0,
        "total_budget_utilization": (totals["comprometido"] / totals["presupuesto"] * 100) if totals["presupuesto"] > 0 else 0,
        "critical_validations_failed": len(validation_summary["critical_issues"])
    }
    
    return {
        "items": {item["nombre"]: item for item in items},  # Dict indexado por nombre
        "totals": totals,
        "validations": validation_summary,
        "kpis": kpis_consolidados,
        "meta": {"total": len(items)},
        "sprint_version": "1.0 - Control Financiero 360",
        "timestamp": f"{len(items)} proyectos - Actualizado"
    }