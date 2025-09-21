#!/usr/bin/env python3
from __future__ import annotations

import re
import unicodedata

NBSP = chr(0x00A0)
NNBSP = chr(0x202F)


def norm_text(s: str | None) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace(NBSP, " ")
    return s


def norm_colname(s: str | None) -> str:
    s = norm_text(s).lower()
    for ch in (' ', '-', '/', '\\', '.', ',', ':', ';', '(', ')', '[', ']', '{', '}'):
        s = s.replace(ch, "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_")


def parse_number(val: str | int | float | None, decimal: str | None = None) -> float:
    """Parse numeric strings tolerant to various locale formats and symbols."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if s == "":
        return 0.0

    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    if s.endswith("-"):
        negative = True
        s = s[:-1]
    if s.startswith("-"):
        negative = True
        s = s[1:]

    s = s.replace(NBSP, "").replace(NNBSP, "").replace(" ", "")
    for symbol in ("$", "CLP", "USD", "EUR", "GBP", "CHF", "CAD", "MXN", "ARS"):
        s = s.replace(symbol, "")
    s = re.sub(r"[^0-9.,-]", "", s)
    if s == "":
        return 0.0

    if decimal not in (",", "."):
        last_comma = s.rfind(",")
        last_dot = s.rfind(".")
        if last_comma == -1 and last_dot == -1:
            decimal = "."
        elif last_comma == -1:
            decimal = "."
        elif last_dot == -1:
            decimal = ","
        else:
            decimal = "," if last_comma > last_dot else "."

    if decimal == ",":
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")

    if s.count(".") > 1:
        head, tail = s.rsplit(".", 1)
        head = head.replace(".", "")
        s = head + "." + tail

    try:
        value = float(s)
    except ValueError:
        return 0.0
    return -value if negative else value
