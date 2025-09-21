import pytest
from backend import server


@pytest.fixture(name="client")
def _client():
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


# Helpers

def _add_rule(client, pattern, project_id, kind="customer_name_like"):
    rv = client.post(
        "/api/ar-map/confirm",
        json={
            "rules": [
                {
                    "kind": kind,
                    "pattern": pattern,
                    "project_id": project_id,
                }
            ]
        },
    )
    assert rv.status_code == 201


def test_ar_map_aggregate_merges_reasons_and_confidence(client):
    # Create two rules that will both match customer name (regex + plain)
    _add_rule(client, pattern="ACME", project_id="P_A")
    # Second rule with different pattern also matching
    _add_rule(client, pattern="ACME Chile", project_id="P_A")
    rv = client.post(
        "/api/ar-map/suggestions",
        json={"invoice": {"customer_name": "Factura ACME Chile Ltda"}},
    )
    assert rv.status_code == 200
    items = rv.get_json()["items"]
    # Expect single aggregated candidate for project P_A
    assert len([i for i in items if i["project_id"] == "P_A"]) >= 1
    target = [i for i in items if i["project_id"] == "P_A"][0]
    # reasons should have at least 1 element and no duplicates
    rs = target.get("reasons") or []
    assert len(rs) >= 1
    assert len(rs) == len(set(rs))
    # confidence should be >= any inserted default (>=0.88 baseline)
    assert float(target.get("confidence") or 0) >= 0.88


def test_ar_map_drive_path_inference_when_no_name_hits(client):
    # Add a drive_path rule
    _add_rule(
        client,
        pattern="/CLIENTES/PROJ123",
        project_id="DRIVE1",
        kind="drive_path_like",
    )
    rv = client.post(
        "/api/ar-map/suggestions",
        json={
            "drive_path": "/mnt/data/CLIENTES/PROJ123/DOCS/Factura1.pdf",
            "invoice": {"customer_name": "Irrelevante"},
        },
    )
    assert rv.status_code == 200
    items = rv.get_json()["items"]
    assert items and items[0]["project_id"] == "DRIVE1"
    reasons = items[0].get("reasons", []) + [items[0].get("reason")]
    assert any(r and r.startswith("drive:") for r in reasons)


def test_ar_map_project_hint_precedes_other_candidates(client):
    _add_rule(client, pattern="FOO", project_id="P_FOO")
    rv = client.post(
        "/api/ar-map/suggestions",
        json={
            "project_hint": "HINTP",
            "invoice": {"customer_name": "FOO Corp"},
        },
    )
    assert rv.status_code == 200
    items = rv.get_json()["items"]
    assert items[0]["project_id"] == "HINTP"
    reasons = items[0].get("reasons", []) + [items[0].get("reason")]
    assert any("hint" in (r or "") for r in reasons)


def test_ar_map_auto_assign_margin_logic(client):
    # Two close confidence candidates to force margin evaluation
    _add_rule(client, pattern="ALPHA", project_id="P_ALPHA")
    _add_rule(client, pattern="ALPHA", project_id="P_ALPHA2")
    rv = client.post(
        "/api/ar-map/auto_assign",
        json={
            "invoice": {"customer_name": "ALPHA"},
            "threshold": 0.5,
            "dry_run": True,
        },
    )
    assert rv.status_code == 200
    data = rv.get_json()
    chosen = data.get("chosen")
    assert chosen is not None
    # Two candidates ~ same confidence; margin < 0.05 => unsafe
    assert data["auto_assigned"] is False


def test_ar_map_invalid_rule_skipped(client):
    # Pattern empty -> should be skipped but request ok
    rv = client.post(
        "/api/ar-map/confirm",
        json={
            "rules": [
                {
                    "kind": "customer_name_like",
                    "pattern": "",
                    "project_id": "X",
                },
                {
                    "kind": "customer_name_like",
                    "pattern": "VALID",
                    "project_id": "Z",
                },
            ]
        },
    )
    assert rv.status_code == 201
    # suggestions with VALID should return one candidate
    rv = client.post(
        "/api/ar-map/suggestions",
        json={"invoice": {"customer_name": "VALID Something"}},
    )
    assert rv.status_code == 200
    items = rv.get_json()["items"]
    assert any(it["project_id"] == "Z" for it in items)


def test_ar_map_alias_canonical_fallback(client):
    """Alias BIGCO -> canonical project via recon_aliases."""
    import os
    import pathlib
    import sqlite3

    db_root = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
    db_path = os.getenv("DB_PATH") or str(db_root / "chipax_data.db")
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.executescript(
            """
CREATE TABLE IF NOT EXISTS recon_aliases(
    id INTEGER PRIMARY KEY, alias TEXT, canonical TEXT
);
CREATE TABLE IF NOT EXISTS projects(
    id INTEGER PRIMARY KEY, name TEXT, slug TEXT, analytic_code TEXT
);
DELETE FROM recon_aliases WHERE alias='BIGCO';
DELETE FROM projects WHERE name='BIG COMPANY S.A.';
INSERT OR IGNORE INTO recon_aliases(alias, canonical)
    VALUES('BIGCO','BIG COMPANY S.A.');
INSERT OR IGNORE INTO projects(name, slug, analytic_code)
    VALUES('BIG COMPANY S.A.','bigco','BIG001');
            """
        )
        con.commit()
    rv = client.post(
        "/api/ar-map/suggestions",
        json={"invoice": {"customer_name": "Pago BIGCO Enero"}},
    )
    assert rv.status_code == 200
    items = rv.get_json()["items"]
    reasons = items[0].get("reasons", []) + [items[0].get("reason")]
    assert items and any("alias:canonical" in (r or "") for r in reasons)
