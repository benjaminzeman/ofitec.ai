#!/usr/bin/env python3
"""One-off/idempotent migration for AP Match tables.

Usage:
    python tools/migrate_ap_match_schema.py

Steps:
 1. Backup legacy tables (rename) if legacy columns detected.
 2. Recreate modern schema for ap_po_links (invoice_id,...).
 3. Preserve data mapping (ap_invoice_id -> invoice_id, line_id -> po_line_id,
        user_id -> created_by).
 4. Leave legacy copy as ap_po_links_legacy_bk (do not drop automatically).
 5. Prepare modern ap_match_events if only legacy 'payload' structure exists.

Safe to re-run: it checks presence of new columns and skips if already
migrated.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
import shutil

from backend.api_ap_match import DB_PATH, _connect_db


def ensure_backup_copy(db_path: str) -> None:
    p = Path(db_path)
    if not p.exists():
        raise SystemExit(f"DB not found: {db_path}")
    backup_path = p.with_suffix(p.suffix + '.pre_ap_match_migration.bak')
    if not backup_path.exists():
        shutil.copy2(p, backup_path)
        print(f"[+] Backup created: {backup_path.name}")
    else:
        print(f"[=] Backup already exists: {backup_path.name}")


def migrate_ap_po_links(conn: sqlite3.Connection) -> None:
    cur = conn.execute("PRAGMA table_info(ap_po_links)")
    cols = [r[1] for r in cur.fetchall()]
    if not cols:
        print("[=] ap_po_links table absent (nothing to migrate)")
        return
    if 'invoice_id' in cols:
        print("[=] ap_po_links already modern schema")
        return
    if 'ap_invoice_id' not in cols:
        print("[!] Unknown schema shape for ap_po_links; aborting.")
        return
    print("[+] Migrating ap_po_links legacy -> modern")
    conn.execute("ALTER TABLE ap_po_links RENAME TO ap_po_links_legacy_bk")
    conn.executescript(
        """
        CREATE TABLE ap_po_links (
            id INTEGER PRIMARY KEY,
            invoice_id INTEGER NOT NULL,
            invoice_line_id INTEGER,
            po_id TEXT,
            po_line_id TEXT,
            amount REAL NOT NULL,
            qty REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_ap_po_links_inv
            ON ap_po_links(invoice_id);
        CREATE INDEX IF NOT EXISTS idx_ap_po_links_pol
            ON ap_po_links(po_line_id);
        """
    )
    # Copy forward
    conn.execute(
        """
        INSERT INTO ap_po_links(
          invoice_id, po_id, po_line_id, amount, created_by, created_at
        )
        SELECT ap_invoice_id, po_id, line_id, amount, user_id, created_at
        FROM ap_po_links_legacy_bk
        """
    )
    row_count = conn.execute(
        "SELECT COUNT(*) FROM ap_po_links"
    ).fetchone()[0]
    print("[+] ap_po_links migrated. Rows:", row_count)


def migrate_ap_match_events(conn: sqlite3.Connection) -> None:
    cur = conn.execute("PRAGMA table_info(ap_match_events)")
    cols = [r[1] for r in cur.fetchall()]
    if not cols:
        print("[=] ap_match_events absent (will be created lazily by API)")
        return
    if 'invoice_id' in cols:
        print("[=] ap_match_events already modern schema")
        return
    if 'payload' in cols:
        print(
            "[+] Creating parallel modern ap_match_events table "
            "(preserving legacy)"
        )
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS ap_match_events (
              id INTEGER PRIMARY KEY,
              invoice_id INTEGER NOT NULL,
              source_json TEXT NOT NULL,
              candidates_json TEXT NOT NULL,
              chosen_json TEXT,
              confidence REAL,
              reasons TEXT,
              accepted INTEGER,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP,
              user_id TEXT
            );
            """
        )
        print(
            "[+] Modern ap_match_events ensured (legacy left intact if "
            "previously different)"
        )
    else:
        print("[!] Unknown ap_match_events schema; skipping.")


def main() -> int:
    ensure_backup_copy(DB_PATH)
    conn = _connect_db()
    try:
        migrate_ap_po_links(conn)
        migrate_ap_match_events(conn)
        conn.commit()
    finally:
        conn.close()
    print("[✓] Migration complete")
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
