"""Simple micro benchmark for a historial-style recon_links query.

Usage (example):
  python tools/bench_recon_links_query.py --iterations 50

It warms once, then times repeated executions of a representative SELECT
joining a subset of tables. Aimed to gauge benefit of indexes.

This is intentionally lightweight and prints JSON so it can be parsed.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from typing import List

from backend.db_utils import db_conn

HISTORIAL_QUERY = (
    "SELECT l.id,l.amount,l.reconciliation_id,"
    " l.bank_movement_id,l.sales_invoice_id,l.purchase_invoice_id"
    " FROM recon_links l"
    " ORDER BY l.id DESC LIMIT 200"
)


def run_once() -> int:
    with db_conn() as c:
        cur = c.execute(HISTORIAL_QUERY)
        rows = cur.fetchall()
        return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=20)
    ap.add_argument("--explain", action="store_true", help="Print EXPLAIN QUERY PLAN and exit")
    args = ap.parse_args()

    if args.explain:
        with db_conn() as c:
            cur = c.execute(f"EXPLAIN QUERY PLAN {HISTORIAL_QUERY}")
            rows = cur.fetchall()
            print(json.dumps({"explain": rows}, indent=2))
        return

    # Warm
    run_once()

    timings: List[float] = []
    for _ in range(args.iterations):
        t0 = time.perf_counter()
        run_once()
        timings.append(time.perf_counter() - t0)

    out = {
        "iterations": args.iterations,
        "mean_sec": statistics.mean(timings),
        "p95_sec": sorted(timings)[int(len(timings) * 0.95) - 1],
        "min_sec": min(timings),
        "max_sec": max(timings),
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
