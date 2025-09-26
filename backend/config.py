#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OFITEC.AI - CONFIGURACIÓN Y UTILIDADES CENTRALIZADAS
==================================================

Módulo centralizado para configuración, carga de entorno y utilidades comunes.
Extraído de server.py para mejor organización y mantenibilidad.
"""

from __future__ import annotations
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional


# ----------------------------------------------------------------------------
# Configuración de Logging
# ----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Rutas del Proyecto
# ----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DOCS_OFICIALES_DIR = PROJECT_ROOT / "docs"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
REPORTES_DIR = BASE_DIR / "reportes"
BADGES_DIR = PROJECT_ROOT / "badges"


# ----------------------------------------------------------------------------
# Carga de Variables de Entorno
# ----------------------------------------------------------------------------

def _load_env_file(path: str) -> None:
    """Carga variables de entorno desde archivo .env de manera segura."""
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)
    except Exception:
        # Silencioso: si falla, seguimos con el entorno actual
        pass


# Cargar configuración de entorno
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
_load_env_file(ENV_PATH)


# ----------------------------------------------------------------------------
# Configuración de Base de Datos
# ----------------------------------------------------------------------------

def get_db_path() -> str:
    """Obtiene la ruta de la base de datos desde configuración."""
    _raw_db = os.getenv("DB_PATH")
    if _raw_db:
        if os.path.isabs(_raw_db):
            return _raw_db
        else:
            return str(PROJECT_ROOT / _raw_db)
    return str(PROJECT_ROOT / "data" / "chipax_data.db")


DB_PATH = get_db_path()


# ----------------------------------------------------------------------------
# Configuración de Rate Limiting
# ----------------------------------------------------------------------------

# Rate limiting configuration
RATE_LIMIT_ENABLED = True
RATE_LIMIT_WINDOW_SEC = int(os.getenv("AI_RATE_LIMIT_WINDOW", "60"))
RATE_LIMIT_MAX = int(os.getenv("AI_RATE_LIMIT_MAX", "30"))

# AI Configuration
AI_SUMMARY_CACHE_TTL = int(os.getenv("AI_SUMMARY_CACHE_TTL", "60"))
AI_JOB_MAX = int(os.getenv("AI_JOB_MAX", "200"))
AI_JOB_TTL_SEC = int(os.getenv("AI_JOB_TTL_SEC", "600"))  # 10 min default

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


# ----------------------------------------------------------------------------
# Utilidades de Filtros
# ----------------------------------------------------------------------------


def build_filters(args, mapping: Dict[str, str]) -> Dict[str, str]:
    """Construye diccionario de filtros desde argumentos de request."""
    return {
        k: v
        for k, v in (
            (alias, args.get(src, type=str)) for alias, src in mapping.items()
        )
        if v is not None
    }


# ----------------------------------------------------------------------------
# Utilidades de Trimming para AI
# ----------------------------------------------------------------------------


def trim_events(seq: list[dict], max_items: int, max_field: int) -> list[dict]:
    """Trim a list of event dicts limiting number of items and max string field length.

    Args:
        seq: Original sequence of event dictionaries.
        max_items: Maximum number of events to retain.
        max_field: Maximum length of any string field value.
    Returns:
        Trimmed list of event dictionaries.
    """
    out: list[dict] = []
    for r in seq[:max_items]:
        nr: Dict[str, Any] = {}
        for k, v in r.items():
            if isinstance(v, str) and len(v) > max_field:
                nr[k] = v[:max_field] + "…"
            else:
                nr[k] = v
        out.append(nr)
    return out


# ----------------------------------------------------------------------------
# Configuración de Prometheus (si está disponible)
# ----------------------------------------------------------------------------


try:
    from prometheus_client import Counter, Histogram, Gauge
    METRICS_ENABLED = True
    
    # Métricas AI
    AI_CALLS = Counter("ai_endpoint_calls_total", "Total AI endpoint invocations", ["endpoint", "result"])
    AI_LAT = Histogram("ai_endpoint_latency_seconds", "Latency of AI calls", ["endpoint"])
    AI_JOBS_ACTIVE = Gauge("ai_jobs_active", "Current number of active (running) AI async jobs")
    AI_JOBS_TOTAL = Counter("ai_jobs_created_total", "Total async AI jobs created")
    AI_JOBS_PRUNED = Counter("ai_jobs_pruned_total", "Total async AI jobs pruned (ttl+max)")
    
except (ImportError, ValueError):
    # Fallback to no-op stubs if prometheus not available or already registered
    METRICS_ENABLED = False
    
    class _MetricsStub:
        def labels(self, *_, **__): return self
        def inc(self, *_, **__): return None
        def observe(self, *_, **__): return None
        def dec(self, *_, **__): return None
        def set(self, *_, **__): return None
    
    AI_CALLS = AI_LAT = AI_JOBS_ACTIVE = AI_JOBS_TOTAL = AI_JOBS_PRUNED = _MetricsStub()


# ----------------------------------------------------------------------------
# Configuración Prometheus Dinámica
# ----------------------------------------------------------------------------

_prometheus_counters: Dict[str, Any] = {}
_prometheus_histograms: Dict[str, Any] = {}


def get_prometheus_counter(name: str, description: str, labels: Optional[List[str]] = None):
    """Get or create a Prometheus counter."""
    if not METRICS_ENABLED:
        return _MetricsStub()
    
    if name not in _prometheus_counters:
        _prometheus_counters[name] = Counter(name, description, labels or [])
    return _prometheus_counters[name]


def get_prometheus_histogram(name: str, description: str, labels: Optional[List[str]] = None):
    """Get or create a Prometheus histogram."""
    if not METRICS_ENABLED:
        return _MetricsStub()
    
    if name not in _prometheus_histograms:
        _prometheus_histograms[name] = Histogram(name, description, labels or [])
    return _prometheus_histograms[name]


def reset_prometheus_metrics():
    """Reset all Prometheus metrics - useful for testing."""
    global _prometheus_counters, _prometheus_histograms
    
    if not METRICS_ENABLED:
        return
    
    try:
        # Clear our internal caches
        _prometheus_counters.clear()
        _prometheus_histograms.clear()
        
        # Clear the default registry
        import prometheus_client
        prometheus_client.REGISTRY._collector_to_names.clear()
        prometheus_client.REGISTRY._names_to_collectors.clear()
    except Exception:
        # If cleanup fails, just continue
        pass


# ----------------------------------------------------------------------------
# Configuración Validada
# ----------------------------------------------------------------------------

def validate_config() -> Dict[str, Any]:
    """Validate current configuration and return status."""
    issues = []
    
    # Check database path
    if not os.path.exists(DB_PATH):
        issues.append(f"Database file not found: {DB_PATH}")
    
    # Check OpenAI API key
    if not OPENAI_API_KEY:
        issues.append("OpenAI API key not configured")
    elif OPENAI_API_KEY.startswith("sk-") and len(OPENAI_API_KEY) < 20:
        issues.append("OpenAI API key appears invalid")
    
    # Check rate limiting config
    if RATE_LIMIT_ENABLED:
        if RATE_LIMIT_MAX <= 0:
            issues.append("Invalid rate limit max value")
        if RATE_LIMIT_WINDOW_SEC <= 0:
            issues.append("Invalid rate limit window")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "config": {
            "db_path": DB_PATH,
            "rate_limiting": RATE_LIMIT_ENABLED,
            "cache_ttl": AI_SUMMARY_CACHE_TTL,
            "prometheus_enabled": bool(METRICS_ENABLED),
        }
    }


logger.info(f"🔧 Configuración cargada - DB: {DB_PATH}, Métricas: {'✅' if METRICS_ENABLED else '❌'}")
