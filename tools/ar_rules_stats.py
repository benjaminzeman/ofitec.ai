#!/usr/bin/env python3
"""Quick AR rules & coverage stats.

Reads the SQLite DB (default data/chipax_data.db or $DB_PATH) and prints a JSON
object with:
  - rules_total: total rows in ar_project_rules
  - rules_by_kind: {kind: count}
  - invoices_total: sales_invoices rows
  - invoices_with_project: sales_invoices rows having non-empty project_id
  - project_assign_rate: fraction (4 decimals) or null if no invoices
  - distinct_customer_names: number of distinct non-empty customer_name
  - customer_names_with_rule: distinct customer names that exactly match a
    customer_name_like rule pattern
  - customer_name_rule_coverage: fraction of distinct names covered by a rule
  - recent_events: ar_map_events count (last 30 days if created_at available)

Usage:
  python tools/ar_rules_stats.py --db data/chipax_data.db

Exit code is 0 even if some tables are missing (fields will be 0 / null) to
stay automation-friendly.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any


def safe_exec(cur: sqlite3.Cursor, sql: str, params=()):
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    except sqlite3.Error:
        return []


def main() -> int:
    ap = argparse.ArgumentParser(description="AR rules coverage stats")
    ap.add_argument("--db", default=os.environ.get("DB_PATH", "data/chipax_data.db"))
    args = ap.parse_args()
    db_path = os.path.abspath(args.db)

    if not os.path.exists(db_path):
        print(json.dumps({"error": f"db not found: {db_path}"}))
        return 0

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    out: Dict[str, Any] = {}

    # Rules
    rows = safe_exec(cur, "SELECT kind, COUNT(1) FROM ar_project_rules GROUP BY kind")
    rules_by_kind = {k: int(c) for k, c in rows}
    out["rules_by_kind"] = rules_by_kind
    out["rules_total"] = sum(rules_by_kind.values())

    # Invoices & assignment
    rows = safe_exec(cur, "SELECT COUNT(1) FROM sales_invoices")
    invoices_total = int(rows[0][0]) if rows else 0
    out["invoices_total"] = invoices_total
    rows = safe_exec(
        cur,
        "SELECT COUNT(1) FROM sales_invoices WHERE TRIM(COALESCE(project_id,'')) <> ''",
    )
    invoices_with_project = int(rows[0][0]) if rows else 0
    out["invoices_with_project"] = invoices_with_project
    out["project_assign_rate"] = round(
        invoices_with_project / invoices_total, 4
    ) if invoices_total else None

    # Coverage of customer_name_like rules
    rows = safe_exec(
        cur,
        "SELECT COUNT(DISTINCT TRIM(COALESCE(customer_name,''))) FROM sales_invoices WHERE TRIM(COALESCE(customer_name,'')) <> ''",
    )
    distinct_names = int(rows[0][0]) if rows else 0
    out["distinct_customer_names"] = distinct_names
    rows = safe_exec(
        cur,
        """
        SELECT COUNT(DISTINCT si.customer_name)
        FROM sales_invoices si
        JOIN ar_project_rules r ON r.kind='customer_name_like' AND r.pattern=si.customer_name
        WHERE TRIM(COALESCE(si.customer_name,'')) <> ''
        """,
    )
    covered_names = int(rows[0][0]) if rows else 0
    out["customer_names_with_rule"] = covered_names
    out["customer_name_rule_coverage"] = round(
        covered_names / distinct_names, 4
    ) if distinct_names else None

    # Recent events (30 days)
    # Only works if created_at column exists and is ISO or close; else returns 0
    cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat(timespec="seconds")
    rows = safe_exec(
        cur,
        "SELECT COUNT(1) FROM ar_map_events WHERE created_at >= ?",
        (cutoff,),
    )
    out["recent_events_30d"] = int(rows[0][0]) if rows else 0

    print(json.dumps(out, ensure_ascii=False))
    conn.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
