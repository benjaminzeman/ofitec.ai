#!/usr/bin/env python3
"""
Promote frequent AR mapping patterns to ar_project_rules.

Strategy (initial):
- Learn customer_name -> project_id pairs from confirmed assignments in
    sales_invoices and/or recent ar_map_events payloads.
- For names seen >= min_count with a single dominant project_id, create a rule
        kind='customer_name_like' with pattern = the exact name,
        confidence tuned by
    frequency.
- Dry-run option prints planned inserts.

Usage:
    python tools/promote_ar_rules.py \
        --db data/chipax_data.db --min-count 3 --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, Tuple

import sys
if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent))
from common_db import default_db_path


def ensure_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ar_project_rules(
          id INTEGER PRIMARY KEY,
          kind TEXT NOT NULL,
          pattern TEXT NOT NULL,
          project_id TEXT NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          created_by TEXT
        );
        CREATE TABLE IF NOT EXISTS ar_map_events(
          id INTEGER PRIMARY KEY,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          user_id TEXT,
          payload TEXT
        );
        """
    )


def learn_from_sales_invoices(
    conn: sqlite3.Connection,
) -> Dict[Tuple[str, str], int]:
    cur = conn.cursor()
    try:
        cur.execute(
            (
                "SELECT TRIM(COALESCE(customer_name,'')) AS name, "
                "TRIM(COALESCE(project_id,'')) AS pid, COUNT(1) AS cnt "
                "FROM sales_invoices WHERE "
                "TRIM(COALESCE(customer_name,'')) <> '' "
                "AND TRIM(COALESCE(project_id,'')) <> '' "
                "GROUP BY name, pid"
            )
        )
        stats: Dict[Tuple[str, str], int] = {}
        for name, pid, cnt in cur.fetchall():
            stats[(str(name), str(pid))] = int(cnt or 0)
        return stats
    except sqlite3.Error:
        return {}


def learn_from_events(conn: sqlite3.Connection) -> Dict[Tuple[str, str], int]:
    cur = conn.cursor()
    stats: Dict[Tuple[str, str], int] = {}
    try:
        cur.execute(
            "SELECT payload FROM ar_map_events ORDER BY id DESC LIMIT 500"
        )
        rows = cur.fetchall()
        for (payload,) in rows:
            try:
                obj = json.loads(payload or "{}")
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
            invoice = obj.get("invoice") or {}
            name = str(invoice.get("customer_name") or "").strip()
            pid = (
                str(obj.get("project_id") or "").strip()
                or str(
                    (obj.get("assignment") or {}).get("project_id") or ""
                ).strip()
                or str(
                    (obj.get("rules") or [{}])[0].get("project_id") or ""
                ).strip()
            )
            if name and pid:
                stats[(name, pid)] = stats.get((name, pid), 0) + 1
    except sqlite3.Error:
        pass
    return stats


def upsert_rules(
    conn: sqlite3.Connection,
    pairs: Dict[Tuple[str, str], int],
    min_count: int,
    dry_run: bool,
    created_by: str,
) -> int:
    total = 0
    for (name, pid), cnt in pairs.items():
        if cnt < min_count:
            continue
        # Avoid duplicate patterns for same project
        cur = conn.execute(
            (
                "SELECT 1 FROM ar_project_rules WHERE "
                "kind='customer_name_like' AND pattern=? AND project_id=?"
            ),
            (name, str(pid)),
        )
        if cur.fetchone():
            continue
        total += 1
        if not dry_run:
            conn.execute(
                (
                    "INSERT INTO ar_project_rules("
                    "kind, pattern, project_id, created_by) VALUES(?,?,?,?)"
                ),
                ("customer_name_like", name, str(pid), created_by),
            )
    if not dry_run:
        conn.commit()
    return total


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--db", default=os.environ.get("DB_PATH", default_db_path(False))
    )
    ap.add_argument("--min-count", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--created-by", default="batch")
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    conn = sqlite3.connect(db_path)
    try:
        ensure_tables(conn)
        s1 = learn_from_sales_invoices(conn)
        s2 = learn_from_events(conn)
        # Merge counts
        all_pairs: Dict[Tuple[str, str], int] = {}
        for k, v in s1.items():
            all_pairs[k] = all_pairs.get(k, 0) + v
        for k, v in s2.items():
            all_pairs[k] = all_pairs.get(k, 0) + v
        promoted = upsert_rules(
            conn, all_pairs, args.min_count, args.dry_run, args.created_by
        )
        print(
            {
                "learned_pairs": len(all_pairs),
                "promoted_rules": promoted,
                "dry_run": args.dry_run,
            }
        )
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
