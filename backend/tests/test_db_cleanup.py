"""
Database cleanup utilities for test isolation and maintenance.
Ensures test databases don't accumulate and consume disk space.
"""
import os
import sqlite3
import tempfile
import atexit
from pathlib import Path


class TestDBManager:
    """Manages test database creation and cleanup."""
    
    def __init__(self):
        self.temp_dbs = []
        atexit.register(self.cleanup_all)
    
    def create_temp_db(self, prefix: str = "test") -> str:
        """Create a temporary database that will be auto-cleaned."""
        # Use system temp directory instead of project data directory
        temp_dir = Path(tempfile.gettempdir()) / "ofitec_tests"
        temp_dir.mkdir(exist_ok=True)
        
        # Create unique temp file
        fd, temp_path = tempfile.mkstemp(suffix='.db', prefix=f'{prefix}_', dir=temp_dir)
        os.close(fd)  # Close the file descriptor
        
        self.temp_dbs.append(temp_path)
        return temp_path
    
    def cleanup_all(self):
        """Clean up all temporary databases."""
        for db_path in self.temp_dbs:
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
            except OSError:
                pass  # File might already be deleted
        self.temp_dbs.clear()
    
    def cleanup_old_test_dbs(self, data_dir: str = "data", max_age_hours: int = 24):
        """Clean up old test databases from data directory."""
        import time
        
        data_path = Path(data_dir)
        if not data_path.exists():
            return
        
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        # Find and remove old test databases
        for pattern in ["test_*.db", "tmp_*.db"]:
            for db_file in data_path.glob(pattern):
                try:
                    if db_file.stat().st_mtime < cutoff_time:
                        db_file.unlink()
                        print(f"Cleaned up old test DB: {db_file.name}")
                except OSError:
                    pass


# Global instance
db_manager = TestDBManager()


def get_test_db(prefix: str = "test") -> str:
    """Get a temporary test database path that will be auto-cleaned."""
    return db_manager.create_temp_db(prefix)


def cleanup_test_dbs():
    """Manual cleanup of test databases."""
    db_manager.cleanup_all()
    db_manager.cleanup_old_test_dbs()


def create_in_memory_db() -> str:
    """Create an in-memory SQLite database for fast tests."""
    return ":memory:"


def ensure_test_schema(db_path: str):
    """Ensure common test tables exist in the database."""
    with sqlite3.connect(db_path) as con:
        # Common tables that tests expect
        con.execute("""
            CREATE TABLE IF NOT EXISTS ar_project_rules(
                id INTEGER PRIMARY KEY,
                kind TEXT,
                pattern TEXT,
                project_id TEXT,
                created_at TEXT,
                created_by TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS ap_match_events(
                id INTEGER PRIMARY KEY,
                candidates_json TEXT,
                confidence REAL,
                accepted INTEGER,
                created_at TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS conciliacion_historial(
                id INTEGER PRIMARY KEY,
                created_at TEXT,
                data_json TEXT
            )
        """)
        con.commit()