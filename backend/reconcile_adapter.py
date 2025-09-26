"""
Adapter para conectar el servidor 5555 con el motor avanzado de conciliación
si está disponible (services/conciliacion_bancaria). Si no, provee un fallback
seguro que retorna 0 sugerencias.
"""
from __future__ import annotations

from typing import Any, Dict, List


def smart_suggest(  # pragma: no cover - opcional externo
    source: Dict[str, Any], options: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Motor inteligente de conciliación usando reconcile_engine.py
    
    Conecta con el motor real entrenado con 6 años de experiencia.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🔍 DEBUG - source: {source}")
        logger.info(f"🔍 DEBUG - options: {options}")
        
        # Importar motor de reconciliación
        import reconcile_engine
        import sqlite3
        
        # Conectar a la base de datos
        db_path = '/app/data/chipax_data.db'
        conn = sqlite3.connect(db_path)
        
        # Obtener movement_id del payload
        movement_id = source.get("id")
        logger.info(f"🔍 DEBUG - movement_id: {movement_id}")
        
        if not movement_id:
            logger.error("❌ DEBUG - No movement_id found")
            return []
            
        # Buscar el movimiento bancario
        movement = reconcile_engine.fetch_bank_movement(conn, movement_id)
        if not movement:
            logger.error(f"❌ DEBUG - No movement found for ID {movement_id}")
            conn.close()
            return []
            
        logger.info(f"✅ DEBUG - Movement: {movement.vendor_name} ${movement.amount:,.0f}")
        
        # Obtener candidatos
        amount_tolerance = options.get("amount_tol", 0.03)
        candidates = reconcile_engine.fetch_candidates(conn, movement, amount_tolerance)
        logger.info(f"✅ DEBUG - Found {len(candidates)} candidates")
        
        # Puntuar candidatos
        suggestions = []
        for candidate in candidates[:10]:  # Solo procesar primeros 10
            suggestion = reconcile_engine.score_candidate(movement, candidate)
            logger.info(f"   Candidate {candidate.id} ({candidate.kind}): confidence {suggestion.confidence:.3f}")
            
            # Convertir a formato esperado por el adaptador
            suggestions.append({
                "candidate": {
                    "target_kind": suggestion.candidate_kind,
                    "kind": suggestion.candidate_kind,
                    "id": suggestion.candidate_id,
                    "doc": suggestion.candidate_id,
                    "amount": candidate.amount,
                    "monto": candidate.amount,
                    "fecha": candidate.date.isoformat() if candidate.date else None,
                    "date": candidate.date.isoformat() if candidate.date else None
                },
                "confidence": suggestion.confidence,
                "score": suggestion.confidence,
                "reasons": [{"rule": ev.rule, "detail": ev.detail, "score": ev.score}
                            for ev in suggestion.evidences]
            })
        
        # Filtrar por umbral de confianza mínima
        min_confidence = 0.3  # Ajustable
        filtered = [s for s in suggestions if s["confidence"] >= min_confidence]
        logger.info(f"✅ DEBUG - {len(filtered)} suggestions after filtering (min_confidence: {min_confidence})")
        
        # Ordenar por confianza
        filtered.sort(key=lambda x: x["confidence"], reverse=True)
        
        conn.close()
        result = filtered[:10]  # Top 10 sugerencias
        logger.info(f"✅ DEBUG - Returning {len(result)} suggestions")
        return result
        
    except Exception as e:
        logger.error(f"❌ DEBUG - Error in smart_suggest: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
