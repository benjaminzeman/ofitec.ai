#!/usr/bin/env python3
"""
Utilidades para RUT chileno: normalizar, validar y calcular DV.

Formato normalizado: 'BODY-DV' con DV en mayúscula y sin puntos.
"""

from __future__ import annotations

import re


_RUT_RE = re.compile(r"^\s*0*([0-9]+)[\-\s]?([0-9Kk])?\s*$")


def compute_dv(body: str) -> str:
    s = 0
    factors = [2, 3, 4, 5, 6, 7]
    digits = list(map(int, reversed(body)))
    for i, d in enumerate(digits):
        s += d * factors[i % len(factors)]
    mod = 11 - (s % 11)
    if mod == 11:
        return "0"
    if mod == 10:
        return "K"
    return str(mod)


def normalize_rut(value: str | None, compute_missing_dv: bool = True) -> str | None:
    """Normaliza un RUT a 'BODY-DV'. Devuelve None si no es interpretable."""
    if not value:
        return None
    m = _RUT_RE.match(str(value))
    if not m:
        return None
    body, dv = m.group(1), m.group(2)
    body = str(int(body))  # quita ceros a la izquierda
    if not dv and compute_missing_dv:
        dv = compute_dv(body)
    if not dv:
        return None
    return f"{body}-{dv.upper()}"


def is_valid_rut(value: str | None) -> bool:
    n = normalize_rut(value, compute_missing_dv=False)
    if not n or "-" not in n:
        return False
    body, dv = n.split("-", 1)
    return compute_dv(body) == dv.upper()

