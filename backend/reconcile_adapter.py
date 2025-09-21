"""
Adapter para conectar el servidor 5555 con el motor avanzado de conciliación
si está disponible (services/conciliacion_bancaria). Si no, provee un fallback
seguro que retorna 0 sugerencias.
"""
from __future__ import annotations

from typing import Any, Dict, List


def smart_suggest(  # pragma: no cover - opcional externo
    _source: Dict[str, Any], _options: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Fallback seguro: sin motor externo retorna 0 sugerencias.

    Si en el futuro integramos el motor inteligente, podemos reemplazar
    esta función para delegar la lógica.
    """
    return []


DEFAULTS = {"amount_tol": 0.01, "days": 5}


def _build_source(context: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "context": context,
        "id": payload.get("id"),
        "amount": payload.get("amount"),
        "date": payload.get("date"),
        "currency": payload.get("currency", "CLP"),
        "ref": payload.get("ref"),
        "extra": payload.get("extra"),
    }


def suggest(context: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    src = _build_source(context, payload)
    opts = {
        "amount_tol": float(payload.get("amount_tol", DEFAULTS["amount_tol"])),
        "days": int(payload.get("days", DEFAULTS["days"])),
    }
    out = smart_suggest(src, opts) or []
    norm: List[Dict[str, Any]] = []
    for it in out:
        cand: Dict[str, Any] = (
            it.get("candidate", {}) if isinstance(it, dict) else {}
        )
        # Permitir variantes de nombres provenientes del motor
        target_kind = (
            cand.get("target_kind")
            or cand.get("kind")
            or cand.get("tipo")
        )
        doc = cand.get("doc") or cand.get("id") or cand.get("ref")
        fecha = cand.get("fecha") or cand.get("date") or cand.get("fecha_doc")
        amount = cand.get("amount") or cand.get("monto") or cand.get("valor")
        score = float(
            it.get("confidence", it.get("score", 0.0) or 0.0)
        )
        reasons = it.get("reasons", [])
        norm.append(
            {
                "target_kind": target_kind,
                "doc": doc,
                "fecha": fecha,
                "amount": amount,
                "score": score,
                "reasons": reasons,
            }
        )
    norm.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return norm[:10]
