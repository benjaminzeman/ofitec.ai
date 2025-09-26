"""
API endpoints para el sistema de validaciones financieras.

Este módulo integra el validation_engine con Flask para proporcionar
endpoints REST que permitan validar reglas de negocio en tiempo real.
"""

import os
import logging
from flask import Blueprint, request, jsonify
from validation_engine import FinancialValidator
from typing import Dict, Any

# Configurar logging
logger = logging.getLogger(__name__)

# Crear blueprint
validation_bp = Blueprint('validation', __name__, url_prefix='/api/validation')

# Instancia global del validador con ruta de BD
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'ofitec_dev.db')
validator = FinancialValidator(DB_PATH)

@validation_bp.route('/invoice_vs_po', methods=['POST'])
def validate_invoice_vs_po():
    """
    Validar que una factura no exceda el monto disponible en la OC.
    
    Body JSON:
    {
        "po_number": "OC001",
        "invoice_amount": 150000.0,
        "po_line_id": "opcional"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "JSON body requerido"
            }), 400
        
        po_number = data.get('po_number')
        invoice_amount = data.get('invoice_amount')
        po_line_id = data.get('po_line_id')
        
        if not po_number or invoice_amount is None:
            return jsonify({
                "error": "po_number e invoice_amount son requeridos"
            }), 400
        
        # Ejecutar validación
        result = validator.validate_invoice_vs_po(po_number, invoice_amount, po_line_id)
        
        return jsonify({
            "is_valid": result.is_valid,
            "flags": [
                {
                    "flag_type": flag.flag_type,
                    "severity": flag.severity,
                    "message": flag.message,
                    "details": flag.details
                }
                for flag in result.flags
            ],
            "validation_type": "invoice_vs_po",
            "validated_at": result.validated_at.isoformat() if result.validated_at else None
        })
        
    except Exception as e:
        logger.error(f"Error en validación factura vs OC: {str(e)}")
        return jsonify({
            "error": f"Error interno: {str(e)}"
        }), 500

@validation_bp.route('/payment_vs_invoice', methods=['POST'])
def validate_payment_vs_invoice():
    """
    Validar que un pago no exceda el saldo pendiente de la factura.
    
    Body JSON:
    {
        "invoice_id": "FAC001",
        "payment_amount": 50000.0
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "JSON body requerido"
            }), 400
        
        invoice_id = data.get('invoice_id')
        payment_amount = data.get('payment_amount')
        
        if not invoice_id or payment_amount is None:
            return jsonify({
                "error": "invoice_id y payment_amount son requeridos"
            }), 400
        
        # Ejecutar validación
        result = validator.validate_payment_vs_invoice(invoice_id, payment_amount)
        
        return jsonify({
            "is_valid": result.is_valid,
            "flags": [
                {
                    "flag_type": flag.flag_type,
                    "severity": flag.severity,
                    "message": flag.message,
                    "details": flag.details
                }
                for flag in result.flags
            ],
            "validation_type": "payment_vs_invoice",
            "validated_at": result.validated_at.isoformat() if result.validated_at else None
        })
        
    except Exception as e:
        logger.error(f"Error en validación pago vs factura: {str(e)}")
        return jsonify({
            "error": f"Error interno: {str(e)}"
        }), 500

@validation_bp.route('/po_vs_budget', methods=['POST'])
def validate_po_vs_budget():
    """
    Validar que una OC no exceda el presupuesto disponible.
    
    Body JSON:
    {
        "po_number": "OC001",
        "po_amount": 200000.0,
        "budget_center": "IT" (opcional)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "JSON body requerido"
            }), 400
        
        po_number = data.get('po_number')
        po_amount = data.get('po_amount')
        budget_center = data.get('budget_center')
        
        if not po_number or po_amount is None:
            return jsonify({
                "error": "po_number y po_amount son requeridos"
            }), 400
        
        # Ejecutar validación
        result = validator.validate_po_vs_budget(po_number, po_amount, budget_center)
        
        return jsonify({
            "is_valid": result.is_valid,
            "flags": [
                {
                    "flag_type": flag.flag_type,
                    "severity": flag.severity,
                    "message": flag.message,
                    "details": flag.details
                }
                for flag in result.flags
            ],
            "validation_type": "po_vs_budget",
            "validated_at": result.validated_at.isoformat() if result.validated_at else None
        })
        
    except Exception as e:
        logger.error(f"Error en validación OC vs presupuesto: {str(e)}")
        return jsonify({
            "error": f"Error interno: {str(e)}"
        }), 500

@validation_bp.route('/invoice_complete', methods=['POST'])
def validate_invoice_complete():
    """
    Ejecutar todas las validaciones aplicables a una factura.
    
    Body JSON:
    {
        "po_number": "OC001",
        "invoice_amount": 150000.0,
        "cost_center": "IT" (opcional),
        "po_line_id": "opcional"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "JSON body requerido"
            }), 400
        
        # Ejecutar validación completa
        result = validator.validate_all_invoice_rules(data)
        
        return jsonify({
            "is_valid": result.is_valid,
            "flags": [
                {
                    "flag_type": flag.flag_type,
                    "severity": flag.severity,
                    "message": flag.message,
                    "details": flag.details
                }
                for flag in result.flags
            ],
            "validation_type": "invoice_complete",
            "validated_at": result.validated_at.isoformat() if result.validated_at else None
        })
        
    except Exception as e:
        logger.error(f"Error en validación completa de factura: {str(e)}")
        return jsonify({
            "error": f"Error interno: {str(e)}"
        }), 500

@validation_bp.route('/flags/<entity_type>/<entity_id>', methods=['GET'])
def get_validation_flags(entity_type, entity_id):
    """
    Obtener flags de validación para una entidad específica.
    
    Args:
        entity_type: Tipo de entidad (invoice, payment, po)
        entity_id: ID de la entidad
    """
    try:
        # Aquí implementaríamos la lógica para recuperar flags almacenados
        # Por ahora returnamos estructura básica
        
        return jsonify({
            "entity_type": entity_type,
            "entity_id": entity_id,
            "flags": [],  # Se implementará con almacenamiento persistente
            "last_validated": None
        })
        
    except Exception as e:
        logger.error(f"Error al obtener flags: {str(e)}")
        return jsonify({
            "error": f"Error interno: {str(e)}"
        }), 500

@validation_bp.route('/rules', methods=['GET'])
def get_validation_rules():
    """
    Obtener información sobre las reglas de validación disponibles.
    """
    return jsonify({
        "rules": [
            {
                "rule_type": "invoice_vs_po",
                "description": "Validar que Factura ≤ OC disponible",
                "endpoint": "/api/validation/invoice_vs_po",
                "required_fields": ["po_number", "invoice_amount"],
                "optional_fields": ["po_line_id"]
            },
            {
                "rule_type": "payment_vs_invoice",
                "description": "Validar que Pago ≤ Factura pendiente",
                "endpoint": "/api/validation/payment_vs_invoice",
                "required_fields": ["invoice_id", "payment_amount"],
                "optional_fields": []
            },
            {
                "rule_type": "po_vs_budget",
                "description": "Validar que OC ≤ Presupuesto disponible",
                "endpoint": "/api/validation/po_vs_budget",
                "required_fields": ["po_number", "po_amount"],
                "optional_fields": ["budget_center"]
            },
            {
                "rule_type": "invoice_complete",
                "description": "Validar todas las reglas aplicables a factura",
                "endpoint": "/api/validation/invoice_complete",
                "required_fields": ["po_number", "invoice_amount"],
                "optional_fields": ["cost_center", "po_line_id"]
            }
        ],
        "flag_severities": ["error", "warning", "info"],
        "flag_types": [
            "po_not_found", "exceeds_po_remaining", "near_po_limit",
            "invoice_not_found", "exceeds_invoice_balance", "completes_invoice",
            "budget_not_found", "exceeds_budget", "high_budget_consumption",
            "validation_error"
        ]
    })

@validation_bp.route('/health', methods=['GET'])
def validation_health():
    """
    Endpoint de salud para el sistema de validaciones.
    """
    try:
        # Test básico de conexión a DB
        validator._get_connection().close()
        
        return jsonify({
            "status": "healthy",
            "message": "Sistema de validaciones operativo",
            "database_connected": True
        })
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "message": f"Error: {str(e)}",
            "database_connected": False
        }), 500