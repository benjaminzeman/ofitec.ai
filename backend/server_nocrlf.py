# Utilidades: RUT chileno

def _rut_compute_dv(body: str) -> str:
    try:
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
    except Exception:
        return ""


def _rut_normalize(rut: str | None) -> str:
    if not rut:
        return ""
    s = "".join(ch for ch in rut if ch.isalnum())
    if not s:
        return ""
    s = s.upper()
    # If ends with letter/digit assume DV present
    if len(s) > 1 and (s[-1].isdigit() or s[-1] == "K"):
        body, dv = s[:-1], s[-1]
    else:
        body, dv = s, _rut_compute_dv(s)
    body = body.lstrip("0") or "0"
    return f"{body}-{dv}"