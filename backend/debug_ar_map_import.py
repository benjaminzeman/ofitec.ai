#!/usr/bin/env python3
"""Debug script to test ar_map import issues"""

import os
import sys

print("Python version:", sys.version)
print("Current working directory:", os.getcwd())
print("Python path:", sys.path[:3])

# Test environment setup
os.environ['DB_PATH'] = 'data/test_debug.db'

try:
    print("\n=== Testing direct import ===")
    import api_ar_map
    print("✅ api_ar_map imported successfully")
    print(f"Module file: {api_ar_map.__file__}")
    print(f"Module dict keys: {list(api_ar_map.__dict__.keys())}")
    
    if hasattr(api_ar_map, 'bp'):
        bp = api_ar_map.bp
        print(f"✅ bp found: {bp}")
        print(f"Blueprint name: {bp.name}")
    else:
        print("❌ No bp attribute found")
        
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n=== Testing from import ===")
    from api_ar_map import bp as ar_map_bp
    print(f"✅ bp imported directly: {ar_map_bp}")
except Exception as e:
    print(f"❌ Direct bp import failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Testing server import ===")
try:
    import server
    print("✅ server imported successfully")
    print(f"Server app: {server.app}")
    
    # Check if AR-MAP blueprint was registered
    blueprint_names = [bp.name for bp in server.app.blueprints.values()]
    print(f"Registered blueprints: {blueprint_names}")
    
    if 'ar_map' in blueprint_names:
        print("✅ ar_map blueprint is registered")
    else:
        print("❌ ar_map blueprint NOT registered")
        
except Exception as e:
    print(f"❌ Server import failed: {e}")
    import traceback
    traceback.print_exc()