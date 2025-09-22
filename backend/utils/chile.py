"""Utilidades Chile (RUT) centralizadas.

Funciones expuestas:
  - rut_normalize(val) -> str | None
  - rut_is_valid(val) -> bool

Se intenta mantener libre de dependencias externas.
"""
from __future__ import annotations

import re
from typing import Optional

_RUT_CLEAN_RE = re.compile(r"[^0-9kK]")


def rut_normalize(val: Optional[str]) -> Optional[str]:
    if not val:
        return val
    s = _RUT_CLEAN_RE.sub("", val).lower()
    if not s:
        return None
    # Último dígito es verificador
    body, dv = s[:-1], s[-1]
    try:
        body_int = int(body)
    except ValueError:
        return None
    return f"{body_int}-{dv}"  # sin puntos; dv en minúscula k o número


def rut_is_valid(val: Optional[str]) -> bool:
    n = rut_normalize(val)
    if not n or "-" not in n:
        return False
    body_str, dv = n.split("-", 1)
    try:
        body = int(body_str)
    except ValueError:
        return False
    # Cálculo módulo 11 estándar
    total = 0
    factor = 2
    while body > 0:
        total += (body % 10) * factor
        body //= 10
        factor += 1
        if factor > 7:
            factor = 2
    mod = 11 - (total % 11)
    if mod == 11:
        expected = "0"
    elif mod == 10:
        expected = "k"
    else:
        expected = str(mod)
    return dv.lower() == expected


__all__ = ["rut_normalize", "rut_is_valid"]
