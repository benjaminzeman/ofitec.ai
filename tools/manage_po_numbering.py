#!/usr/bin/env python3
"""
Manage Ofitec PO numbering sequence.

Usage:
  python tools/manage_po_numbering.py [--db ...] [--name po_number] \
      [--set-prefix PO-] [--set-padding 5] [--set-start 1] [--peek]
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent))
from common_db import default_db_path
from numbering import ensure_sequence, peek_number


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=default_db_path(prefer_root=False))
    ap.add_argument("--name", default="po_number")
    ap.add_argument("--set-prefix")
    ap.add_argument("--set-padding", type=int)
    ap.add_argument("--set-start", type=int)
    ap.add_argument("--peek", action="store_true")
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print("DB not found:", db_path)
        return 2

    conn = sqlite3.connect(db_path)
    try:
        ensure_sequence(
            conn,
            args.name,
            prefix=args.set_prefix,
            padding=args.set_padding,
            start=args.set_start,
        )
        conn.commit()
        if args.peek:
            print("Next number:", peek_number(conn, args.name))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

