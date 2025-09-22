import os
import importlib
import sqlite3
import pytest


@pytest.fixture(scope="function")
def client(tmp_path):
    """Unified test client using a fresh temp DB for isolation.

    Sets DB_PATH env before importing/reloading server so that all modules
    (including api_ar_map & matching metrics) point to the same ephemeral DB.
    """
    db_file = tmp_path / "test.db"
    os.environ["DB_PATH"] = str(db_file)
    # Ensure clean import state
    import backend.server as server
    importlib.reload(server)
    # Pre-create minimal tables often expected to exist implicitly
    with sqlite3.connect(str(db_file)) as con:
        con.execute("CREATE TABLE IF NOT EXISTS ar_project_rules(id INTEGER PRIMARY KEY, kind TEXT, pattern TEXT, project_id TEXT, created_at TEXT, created_by TEXT)")
        con.execute("CREATE TABLE IF NOT EXISTS ap_match_events(id INTEGER PRIMARY KEY, candidates_json TEXT, confidence REAL, accepted INTEGER, created_at TEXT)")
        con.commit()
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def _recon_env_isolation():
    """Ensure per-test isolation of mutable RECON_* env vars that affect logging/metrics.

    Prevent leakage of sampling overrides or disable flags set by previous tests.
    Tests that need specific values simply set them after their fixtures run.
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
    # (No teardown restoration needed; tests set what they need explicitly.)
