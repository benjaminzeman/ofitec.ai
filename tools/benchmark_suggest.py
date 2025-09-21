"""Micro-benchmark for reconciliation suggest endpoint logic.

Goal: Provide a quick, repeatable in-memory latency baseline so future changes
can detect regressions. It intentionally avoids network & DB I/O by mocking
adapter calls and invoking Flask test client directly.

Usage (example):
  PYTHONPATH=. python tools/benchmark_suggest.py --samples 500 --warmup 50

Outputs JSON with: count, warmup, mean, p50, p95, p99, min, max, rps.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import List

from flask import Flask

# Ensure project root in sys.path for direct execution BEFORE backend imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class _FakeAdapter:
    def __init__(self):
        self._payload = [{"score": 0.9, "amount": 123.45, "bank_movement_id": 1}]

    def suggest(self, _context: str, payload):  # signature mimic
        amt = (payload.get("id") or 0) % 7
        return [] if amt == 0 else self._payload


def build_app() -> Flask:
    from backend.conciliacion_api_clean import bp  # type: ignore
    app = Flask("bench")
    app.register_blueprint(bp)
    return app


def percentile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    k = (len(values) - 1) * (q / 100.0)
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return values[f]
    d = k - f
    return values[f] + (values[c] - values[f]) * d


def run(samples: int, warmup: int, movement_id: int, context: str) -> dict:
    from backend import reconcile_adapter  # type: ignore
    from backend.conciliacion_api_clean import test_reset_internal, _metrics_disabled  # type: ignore
    reconcile_adapter.suggest = _FakeAdapter().suggest  # type: ignore
    app = build_app()
    os.environ["RECON_TEST_MODE"] = "1"
    try:
        test_reset_internal()
    except RuntimeError:
        pass  # non-test mode fallback
    latencies: List[float] = []
    payload = {"movement_id": movement_id, "limit": 5, "context": context}
    with app.test_client() as client:
        for i in range(samples + warmup):
            t0 = time.perf_counter()
            rv = client.post("/api/conciliacion/suggest", json=payload)
            if rv.status_code != 200:
                raise RuntimeError(f"unexpected status {rv.status_code}")
            dt = time.perf_counter() - t0
            if i >= warmup:
                latencies.append(dt)
    latencies.sort()
    total = sum(latencies)
    count = len(latencies)
    mean = total / count if count else 0.0
    return {
        "samples": count,
        "warmup": warmup,
        "mean": mean,
        "min": latencies[0] if count else 0.0,
        "max": latencies[-1] if count else 0.0,
        "p50": percentile(latencies, 50),
        "p95": percentile(latencies, 95),
        "p99": percentile(latencies, 99),
        "sum": total,
        "rps": count / total if total else 0.0,
        "metrics_disabled": _metrics_disabled(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=200)
    ap.add_argument("--warmup", type=int, default=30)
    ap.add_argument("--movement-id", type=int, default=123)
    ap.add_argument("--context", default="bank")
    ap.add_argument("--json", action="store_true", help="Emit raw JSON only")
    args = ap.parse_args()
    res = run(args.samples, args.warmup, args.movement_id, args.context)
    if args.json:
        print(json.dumps(res, indent=2))
        return
    print("Suggest micro-benchmark")
    print(f"Samples        : {res['samples']} (warmup {res['warmup']})")
    print(f"Mean (ms)      : {res['mean']*1000:.3f}")
    print(f"P50 / P95 / P99: {res['p50']*1000:.3f} / {res['p95']*1000:.3f} / {res['p99']*1000:.3f} ms")
    print(f"Min / Max (ms) : {res['min']*1000:.3f} / {res['max']*1000:.3f}")
    print(f"Throughput RPS : {res['rps']:.1f}")
    print(f"Metrics disabled: {res['metrics_disabled']}")


if __name__ == "__main__":  # pragma: no cover
    main()
