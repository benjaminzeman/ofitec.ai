#!/usr/bin/env python3
"""Lightweight guard to ensure `backend/conciliacion_api.py` stays a minimal stub.

Intended for pre-commit/CI usage; exits 1 on failure and prints the reason.
"""
from __future__ import annotations

import sys
import ast
from pathlib import Path

STUB_PATH = Path("backend/conciliacion_api.py")
SENTINEL = "# SENTINEL (nothing should follow)"
MAX_BYTES = 1024
EXPECTED_ALL = ["bp"]


def main() -> int:
    if not STUB_PATH.exists():
        print(f"FAIL: stub missing at {STUB_PATH}")
        return 1
    stat = STUB_PATH.stat()
    if stat.st_size > MAX_BYTES:
        print(f"FAIL: stub size {stat.st_size} > {MAX_BYTES}")
        return 1
    text = STUB_PATH.read_text(encoding="utf-8")
    count = text.count(SENTINEL)
    if count != 1:
        print("FAIL: sentinel missing or duplicated")
        return 1
    tail = text.split(SENTINEL, 1)[1].strip()
    if tail:
        print("FAIL: trailing content after sentinel")
        return 1
    if "from .conciliacion_api_clean import bp" not in text:
        print("FAIL: missing clean bp re-export")
        return 1
    try:
        module_ast = ast.parse(text, filename=str(STUB_PATH))
    except SyntaxError as exc:  # pragma: no cover - stub must be valid
        print(f"FAIL: syntax error in stub: {exc}")
        return 1
    exported = None
    for node in module_ast.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        exported = [elt.value for elt in node.value.elts if isinstance(elt, ast.Constant)]
    if exported != EXPECTED_ALL:
        print(f"FAIL: __all__ mismatch: expected {EXPECTED_ALL!r}, got {exported!r}")
        return 1
    print("OK: conciliacion stub is clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
