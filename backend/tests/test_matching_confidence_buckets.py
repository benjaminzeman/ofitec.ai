import re
import sqlite3
import os
from backend.api_matching_metrics import _ap_metrics  # type: ignore


def test_confidence_bucket_labels_pattern(tmp_path):
    # Prepare isolated in-memory DB with required table
    db = tmp_path / 'test.db'
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE ap_match_events (id INTEGER PRIMARY KEY, candidates_json TEXT, confidence REAL, accepted INTEGER, created_at TEXT)")
    # Insert synthetic confidences covering buckets
    samples = [0.05, 0.19, 0.20, 0.21, 0.39, 0.40, 0.59, 0.60, 0.79, 0.80, 0.89, 0.90, 0.949, 0.95, 0.97, 1.0]
    for i, cf in enumerate(samples, start=1):
        con.execute("INSERT INTO ap_match_events(id, candidates_json, confidence, accepted, created_at) VALUES(?,?,?,?, datetime('now'))", (i, '[]', cf, 1 if cf >= 0.5 else 0))
    con.commit()
    # Monkeypatch server DB_PATH if needed (not required here since we call internal helper directly)
    os.environ["AP_METRICS_FORCE_ADVANCED"] = "1"
    metrics = _ap_metrics(con, window_days=0)
    buckets = metrics['confidence_buckets']
    assert buckets, 'Buckets should be computed'
    pattern = re.compile(r"^\d{5}_\d{5}$")
    for label in buckets.keys():
        assert pattern.match(label), f"Label {label} does not match expected 5-digit pattern"
    # Expected bucket keys (ordered by edges in code)
    expected = [
        '00000_02000',
        '02000_04000',
        '04000_06000',
        '06000_08000',
        '08000_09000',
        '09000_09500',
        '09500_10000',
    ]
    assert list(buckets.keys()) == expected, f"Unexpected bucket ordering: {list(buckets.keys())}"
    # Basic distribution sanity (non negative counts; total equals events)
    assert sum(buckets.values()) == len(samples)
    assert all(v >= 0 for v in buckets.values())
    con.close()
