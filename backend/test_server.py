#!/usr/bin/env python3
"""
SERVIDOR DE PRUEBA ULTRA SIMPLE
"""
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"status": "WORKING", "test": "SUCCESS"})

@app.route("/api/status")
def status():
    return jsonify({"status": "OK", "server": "FUNCTIONAL"})

if __name__ == "__main__":
    print("=== INICIANDO SERVIDOR DE PRUEBA ===")
    print("Listening on: http://0.0.0.0:5555")
    app.run(host="0.0.0.0", port=5555, debug=False)