import os
import pytest
from test_db_cleanup import get_test_db, ensure_test_schema, cleanup_test_dbs


@pytest.fixture(scope="function")
def client(tmp_path):
    """Unified test client using a fresh temp DB for isolation.

    Uses the new test database management system to prevent accumulation
    of test databases in the data directory.
    """
    # Use the new test DB manager instead of tmp_path
    db_file = get_test_db("test_client")
    os.environ["DB_PATH"] = str(db_file)
    
    # Clear modules that might have cached DB paths
    import sys
    modules_to_clear = [name for name in sys.modules.keys()
                        if any(x in name for x in ['server', 'sc_ep_api', 'ep_api']) and 'api_ar_map' not in name]
    for module_name in modules_to_clear:
        del sys.modules[module_name]

    # Ensure clean import state
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    import server
    # Don't reload - just import fresh
    
    # Use the new schema setup function
    ensure_test_schema(str(db_file))
    
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def _recon_env_isolation():
    """Ensure per-test isolation of mutable RECON_* env vars that affect logging/metrics.

    Prevent leakage of sampling overrides or disable flags set by previous tests.
    Tests that need specific values simply set them after their fixtures run.
    Also performs cleanup of old test databases periodically.
    """
    # Clear sampling globals/overrides
    for k in list(os.environ.keys()):
        if k.startswith("RECON_STRUCTURED_LOG_SAMPLE_RECON_"):
            os.environ.pop(k, None)
    for k in [
        "RECON_STRUCTURED_LOG_SAMPLE",
        "RECON_DISABLE_METRICS",
        "RECON_METRICS_DISABLED",
        "RECON_STRUCTURED_LOG_ASYNC",
    ]:
        os.environ.pop(k, None)
    
    yield
    
    # Periodic cleanup of old test databases (every 50 tests approximately)
    import random
    if random.randint(1, 50) == 1:
        cleanup_test_dbs()
