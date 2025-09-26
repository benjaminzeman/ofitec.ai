import os
import tempfile

def test_ar_map_direct_import():
    # Set up environment like conftest but without module clearing
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = os.path.join(tmpdir, 'test.db') 
        os.environ['DB_PATH'] = db_file
        
        # Import server fresh (simulating what conftest does)
        import importlib
        import sys
        
        # Only clear server module, keep api_ar_map intact
        if 'server' in sys.modules:
            del sys.modules['server']
        if 'backend.server' in sys.modules:
            del sys.modules['backend.server']
            
        import server
        
        # Check if ar_map blueprint is registered
        blueprint_names = [bp.name for bp in server.app.blueprints.values()]
        print(f'Registered blueprints: {blueprint_names}')
        
        if 'ar_map' in blueprint_names:
            print('✅ AR-MAP blueprint registered')
            
            # Test the endpoint
            client = server.app.test_client()
            resp = client.post('/api/ar-map/suggestions', json={'invoice': {'customer_name': 'Test'}})
            print(f'Response status: {resp.status_code}')
            assert resp.status_code == 200
        else:
            print('❌ AR-MAP blueprint NOT registered')
            assert False, 'AR-MAP blueprint not registered'

if __name__ == '__main__':
    test_ar_map_direct_import()

