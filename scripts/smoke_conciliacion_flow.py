#!/usr/bin/env python3
"""Quick smoke test for conciliacion flow.

Runs a minimal suggest -> confirmar -> historial -> metrics cycle using Flask test client.
Prints key metric lines (p50/p95/p99 + persistence gauges) and exits 0 if all present.

Usage:
  python scripts/smoke_conciliacion_flow.py
Environment (optional):
  RECON_METRICS_DEBUG=1 to allow /metrics/json (ignored if not set)
"""
from __future__ import annotations

import os
import sys
from importlib import import_module

# Ensure clean module is preferred
os.environ.setdefault("RECONCILIACION_CLEAN", "1")

try:
    server = import_module("backend.server")
except Exception as exc:  # pragma: no cover
    print(f"ERROR: cannot import backend.server: {exc}")
    sys.exit(2)

app = getattr(server, "app", None)
if app is None:
    print("ERROR: server.app missing")
    sys.exit(2)

client = app.test_client()

# 1. Suggest (placeholder returns empty)
client.post("/api/conciliacion/suggest", json={"movement_id": 1})
# 2. Confirmar
client.post("/api/conciliacion/confirmar", json={"movement_id": 1})
# 3. Historial
hist = client.get("/api/conciliacion/historial")
if hist.status_code != 200:
    print("ERROR: historial status", hist.status_code)
    sys.exit(3)
# 4. Metrics text
m = client.get("/api/conciliacion/metrics")
if m.status_code != 200:
    print("ERROR: metrics status", m.status_code)
    sys.exit(4)
text = m.get_data(as_text=True)
needed = [
    "recon_suggest_latency_seconds_p50",
    "recon_suggest_latency_seconds_p95",
    "recon_suggest_latency_seconds_p99",
]
missing = [n for n in needed if n not in text]
if missing:
    print("ERROR: missing metrics:", ", ".join(missing))
    sys.exit(5)
print("OK conciliacion smoke | percentiles present")
# Print a small excerpt
for line in text.splitlines():
    if line.startswith("recon_suggest_latency_seconds_p"):
        print(line)
    if line.startswith("recon_persist_"):
        print(line)
sys.exit(0)
