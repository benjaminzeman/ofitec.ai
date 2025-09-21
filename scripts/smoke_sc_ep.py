import json
import sys
from typing import Any, Dict

import requests

BASE = "http://127.0.0.1:5555"


def req(method: str, path: str, payload: Dict[str, Any] | None = None):
    url = f"{BASE}{path}"
    try:
        r = requests.request(method, url, json=payload, timeout=10)
    except Exception as e:  # pragma: no cover
        print(f"REQUEST ERROR {method} {url}: {e}")
        sys.exit(2)
    ct = r.headers.get("content-type", "")
    body: Any
    if "application/json" in ct:
        try:
            body = r.json()
        except Exception:
            body = r.text
    else:
        body = r.text
    print(f"{method} {path} -> {r.status_code}")
    if isinstance(body, (dict, list)):
        print(json.dumps(body, ensure_ascii=False, indent=2))
    else:
        print(body[:500])
    return r.status_code, body


def main() -> int:
    # Ping root
    print("== PING /")
    req("GET", "/")

    # Create SC EP header
    print("\n== CREATE SC EP HEADER")
    status, body = req(
        "POST",
        "/api/sc/ep",
        {
            "project_id": 2306,
            "ep_number": "SC-001",
            "period_start": "2025-08-01",
            "period_end": "2025-08-31",
            "retention_pct": 0.05,
        },
    )
    if status != 201 or not isinstance(body, dict) or "ep_id" not in body:
        print("SC EP header creation failed; aborting.")
        return 1
    ep_id = body["ep_id"]

    # Set lines
    print("\n== SET LINES")
    req(
        "POST",
        f"/api/sc/ep/{ep_id}/lines/bulk",
        {
            "lines": [
                {
                    "item_code": "P1",
                    "description": "Excavation",
                    "unit": "m3",
                    "qty_period": 10,
                    "unit_price": 100000,
                    "qty_cum": 10,
                    "amount_cum": 1000000,
                }
            ]
        },
    )

    # Set deductions
    print("\n== SET DEDUCTIONS")
    req(
        "POST",
        f"/api/sc/ep/{ep_id}/deductions/bulk",
        {
            "deductions": [
                {
                    "type": "advance_amortization",
                    "description": "Advance amortization",
                    "amount": 200000,
                }
            ]
        },
    )

    # Summary
    print("\n== SUMMARY")
    req("GET", f"/api/sc/ep/{ep_id}/summary")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
