#!/usr/bin/env python3
"""Offline validator for structured log lines.

Reads a file (or stdin) of newline-delimited JSON objects and validates that:
  - JSON parses
  - Contains 'event','request_id','timestamp','schema_version'
  - timestamp matches RFC3339 with millisecond precision used by the API
  - schema_version is an int >= 1
Unknown extra fields are allowed.

Exit codes:
 0 success (no errors)
 1 file IO error
 2 validation errors encountered

Usage:
  python -m tools.validate_structured_logs path/to/logfile
  cat logfile | python -m tools.validate_structured_logs -
"""
from __future__ import annotations

import json
import re
import sys
import typing as t

CORE = {"event", "request_id", "timestamp", "schema_version"}
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def _iter_lines(path: str):
    if path == "-":
        for line in sys.stdin:
            yield line.rstrip("\n")
    else:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                yield line.rstrip("\n")


def validate_line(line: str, lineno: int) -> t.List[str]:
    errs: t.List[str] = []
    if not line.strip():
        return errs
    if not line.lstrip().startswith("{"):
        return [f"Line {lineno}: not JSON object start"]
    try:
        obj = json.loads(line)
    except Exception as exc:
        return [f"Line {lineno}: JSON parse error: {exc}"]
    missing = CORE - obj.keys()
    if missing:
        errs.append(f"Line {lineno}: missing keys {sorted(missing)}")
    else:
        ts = obj.get("timestamp")
        if not isinstance(ts, str) or not TS_RE.match(ts):
            errs.append(f"Line {lineno}: invalid timestamp '{ts}'")
        sv = obj.get("schema_version")
        if not isinstance(sv, int) or sv < 1:
            errs.append(f"Line {lineno}: bad schema_version '{sv}'")
        rid = obj.get("request_id")
        if not isinstance(rid, str) or not rid:
            errs.append(f"Line {lineno}: invalid request_id '{rid}'")
    return errs


def main(argv: t.List[str]) -> int:
    if len(argv) != 2:
        print("Usage: validate_structured_logs.py <file|->", file=sys.stderr)
        return 1
    path = argv[1]
    total = 0
    errors = 0
    for lineno, line in enumerate(_iter_lines(path), start=1):
        total += 1
        for err in validate_line(line, lineno):
            print(err, file=sys.stderr)
            errors += 1
    if errors:
        print(f"Validation failed: {errors} error(s) in {total} line(s)", file=sys.stderr)
        return 2
    print(f"OK: {total} line(s) valid", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))
