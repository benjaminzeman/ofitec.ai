#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test server para endpoint control financiero"""

import sys
import os
from flask import Flask, jsonify
import sqlite3
from datetime import datetime

# Asegurar path del backend
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

app = Flask(__name__)

# Path a la BD
DB_PATH = r"C:\Users\benja\OneDrive\Escritorio\0. OFITEC.AI\ofitec.ai\data\chipax_data.db"

@app.route("/api/control_financiero/resumen")
def api_control_financiero_resumen():
    """Test endpoint para Control Financiero 360"""
    try:
        # Importar aquí para evitar problemas
        from control_financiero_adapter import get_control_financiero_data
        
        result = get_control_financiero_data(DB_PATH)
        
        print(f"[SUCCESS] Control Financiero: {result['meta']['total']} proyectos cargados")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[ERROR] En control_financiero: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "error": str(e),
            "items": {},
            "totals": {"presupuesto": 0, "comprometido": 0, "facturado": 0, "pagado": 0, "disponible": 0},
            "meta": {"total": 0, "error": True}
        })

@app.route("/")
def test_home():
    return """
    <h1>Test Control Financiero Server</h1>
    <p><a href="/api/control_financiero/resumen">Test Control Financiero Endpoint</a></p>
    """

if __name__ == "__main__":
    print(f"[INFO] Iniciando servidor test...")
    print(f"[INFO] Database path: {DB_PATH}")
    print(f"[INFO] Backend dir: {BACKEND_DIR}")
    
    app.run(host="127.0.0.1", port=5556, debug=True)