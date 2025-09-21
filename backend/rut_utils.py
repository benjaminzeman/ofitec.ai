"""RUT (Rol Único Tributario) utilities estándar chileno.

Funciones principales:
- normalize_rut: limpia y devuelve cuerpo-DV (mayúscula, sin puntos), calcula DV si falta.
- compute_dv: calcula dígito verificador módulo 11.
- validate_rut: verifica formato y DV correcto.
- format_rut: agrega puntos de miles y guion final a un RUT normalizado o crudo.

Concesiones:
- Acepta dv 'K' o 'k' (se normaliza a 'K').
- Si recibe algo sin dv (solo números) => calcula dv y retorna normalizado.
- Si el cuerpo tiene ceros a la izquierda se eliminan (excepto si todo era 0).
"""
from __future__ import annotations

from typing import Optional

__all__ = [
    "compute_dv",
    "normalize_rut",
    "validate_rut",
    "format_rut",
]


def compute_dv(body: str) -> str:
    body = body.strip()
    if not body.isdigit():
        return ""
    reversed_digits = list(map(int, reversed(body)))
    factors = [2, 3, 4, 5, 6, 7]
    s = 0
    for i, d in enumerate(reversed_digits):
        s += d * factors[i % len(factors)]
    mod = 11 - (s % 11)
    if mod == 11:
        return "0"
    if mod == 10:
        return "K"
    return str(mod)


def normalize_rut(raw: Optional[str]) -> str:
    if not raw:
        return ""
    # Remove dots and spaces; keep digits, K/k and hyphen to detect explicit DV
    raw_str = raw.strip()
    base = "".join(ch for ch in raw_str if ch.isdigit() or ch.upper() == 'K' or ch == '-')
    if not base:
        return ""
    base = base.replace('.', '').upper()
    explicit = '-' in base
    if explicit:
        parts = [p for p in base.split('-') if p]
        if len(parts) != 2:
            return ""
        body, dv = parts
        if not body.isdigit() or not (dv.isdigit() or dv == 'K'):
            return ""
        body_norm = body.lstrip('0') or '0'
        return f"{body_norm}-{dv}"
    # No explicit hyphen: last char could be dv only if alpha K; else compute
    stripped = base
    if len(stripped) >= 2 and stripped[-1] == 'K' and stripped[:-1].isdigit():
        body = stripped[:-1]
        dv = 'K'
        body_norm = body.lstrip('0') or '0'
        return f"{body_norm}-{dv}"
    if stripped.isdigit():
        body = stripped
        dv = compute_dv(body)
        body_norm = body.lstrip('0') or '0'
        return f"{body_norm}-{dv}"
    return ""


def validate_rut(raw: Optional[str]) -> bool:
    norm = normalize_rut(raw)
    if not norm or "-" not in norm:
        return False
    body, dv = norm.split("-", 1)
    if not body.isdigit():
        return False
    return compute_dv(body) == dv.upper()


def format_rut(raw: Optional[str]) -> str:
    norm = normalize_rut(raw)
    if not norm:
        return ""
    body, dv = norm.split("-", 1)
    # thousands separator with dot
    parts = []
    while body:
        parts.append(body[-3:])
        body = body[:-3]
    body_fmt = ".".join(reversed(parts))
    return f"{body_fmt}-{dv}"
