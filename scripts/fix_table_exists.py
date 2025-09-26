#!/usr/bin/env python3
"""
Script to replace all _table_exists() calls with _view_or_table_exists()
"""

import re
from pathlib import Path

# Path to server.py
server_file = Path(__file__).parent.parent / "backend" / "server.py"

# Read the file
with open(server_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all _table_exists calls with _view_or_table_exists
# But NOT the function definition itself
content = re.sub(
    r'(\s+)_table_exists\(',  # Preceded by whitespace (not function definition)
    r'\1_view_or_table_exists(',
    content
)

# Also replace calls that are not preceded by whitespace but are after 'and', 'or', 'if', etc.
content = re.sub(
    r'(and|or|if|elif|not)\s+_table_exists\(',
    r'\1 _view_or_table_exists(',
    content
)

# Write back to file
with open(server_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed all _table_exists() calls to use _view_or_table_exists()")
print(f"📁 Modified: {server_file}")