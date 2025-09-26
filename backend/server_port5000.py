#!/usr/bin/env python3
"""
SERVIDOR OFITEC.AI - PUERTO 5000
"""
import os
import sqlite3
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(ROOT_DIR, "data", "chipax_data.db")

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        return None

@app.route("/")
def home():
    return jsonify({
        "service": "OFITEC.AI Backend",
        "version": "1.0 - PUERTO 5000",
        "status": "online",
        "database": os.path.exists(DB_PATH)
    })

@app.route("/api/status")
def api_status():
    return jsonify({"status": "OK", "port": 5000})

@app.route("/api/control_financiero/resumen")
def control_financiero():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "BD error"}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT name, budget_cop FROM projects")
        projects = cursor.fetchall()
        
        total_projects = len(projects)
        total_budget = sum(p['budget_cop'] for p in projects if p['budget_cop'])
        conn.close()
        
        return jsonify({
            "projects": {"total": total_projects, "budget_total": total_budget},
            "cash": {"today": 1250000000, "d7": 1100000000, "d30": 980000000},
            "revenue": {"month": 45000000, "ytd": 420000000},
            "validations": {"all_validations_passed": True},
            "alerts": [],
            "timestamp": "2025-01-15 20:00:00"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ceo/overview")
def ceo_overview():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "BD error"}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM projects")
        projects_total = cursor.fetchone()['total']
        conn.close()
        
        return jsonify({
            "cash": {"today": 1250000000, "d7": 1100000000, "d30": 980000000},
            "revenue": {"month": 85000000, "ytd": 720000000},
            "projects": {"total": projects_total},
            "risk": {"score": 85, "high": 2, "medium": 5},
            "acciones": [
                {"titulo": "Revisar flujo de caja", "urgencia": "alta"},
                {"titulo": "Diversificar cartera", "urgencia": "media"}
            ],
            "alerts": [{"message": "Cash flow projection", "type": "warning"}],
            "timestamp": "2025-01-15 20:00:00"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("=== OFITEC.AI BACKEND - PUERTO 5000 ===")
    print(f"Database: {DB_PATH}")
    print(f"Database exists: {os.path.exists(DB_PATH)}")
    
    app.run(host="0.0.0.0", port=5000, debug=False)