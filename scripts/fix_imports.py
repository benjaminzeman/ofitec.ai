#!/usr/bin/env python3
"""
Script to fix all backend. import issues by removing the backend. prefix
"""

import re
from pathlib import Path

# Path to server.py
server_file = Path(__file__).parent.parent / "backend" / "server.py"

# Read the file
with open(server_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the pattern and replacement pairs
fixes = [
    (r'from backend\.conciliacion_api_clean import', 'from conciliacion_api_clean import'),
    (r'from backend\.conciliacion_api import', 'from conciliacion_api import'),
    (r'from backend\.api_sales_invoices import', 'from api_sales_invoices import'),
    (r'from backend\.api_ar_map import', 'from api_ar_map import'),
    (r'from backend\.api_sii import', 'from api_sii import'),
    (r'from backend\.api_ap_match import', 'from api_ap_match import'),
    (r'from backend\.api_matching_metrics import', 'from api_matching_metrics import'),
    (r'from backend\.utils\.chile import', 'from utils.chile import'),
    (r'from backend\.ai\.xai_client import', 'from ai.xai_client import'),
]

# Apply all fixes
for pattern, replacement in fixes:
    content = re.sub(pattern, replacement, content)

# Write back to file
with open(server_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed all backend. import prefixes")
print(f"📁 Modified: {server_file}")