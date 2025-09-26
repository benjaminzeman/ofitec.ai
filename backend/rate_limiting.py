#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OFITEC.AI - RATE LIMITING Y CACHING
==================================

Módulo especializado para manejo de rate limiting y caching.
Extraído de server.py para mejor organización.
"""

from __future__ import annotations
import time
import threading
from collections import deque
from typing import Dict, Tuple, Any, Optional
from flask import request
from config import RATE_LIMIT_ENABLED, RATE_LIMIT_WINDOW_SEC, RATE_LIMIT_MAX, AI_SUMMARY_CACHE_TTL

# ----------------------------------------------------------------------------
# Rate Limiting
# ----------------------------------------------------------------------------

_rate_lock = threading.Lock()
_rate_hits: Dict[Tuple[str, str], deque[float]] = {}


def _get_current_rate_limit() -> int:
    """Get current rate limit, allowing for test overrides."""
    try:
        import server
        return getattr(server, '_RATE_LIMIT_MAX', RATE_LIMIT_MAX)
    except ImportError:
        return RATE_LIMIT_MAX


def is_rate_limited(endpoint: str) -> bool:
    """Check if current request is rate limited for given endpoint."""
    if not RATE_LIMIT_ENABLED:
        return False
    
    rate_max = _get_current_rate_limit()
    
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    key = (ip, endpoint)
    now = time.time()
    
    with _rate_lock:
        dq = _rate_hits.setdefault(key, deque())
        # Remove old entries
        cutoff = now - RATE_LIMIT_WINDOW_SEC
        while dq and dq[0] < cutoff:
            dq.popleft()
        
        if len(dq) >= rate_max:
            return True
        
        dq.append(now)
    return False


def retry_after_seconds(endpoint: str) -> int:
    """Compute remaining seconds until a rate-limited caller may retry.

    Returns 0 if not currently limited. Value is ceiling of remaining
    window for the oldest timestamp in the sliding window. Always >=1
    when limited to avoid ambiguous 0-second waits.
    """
    if not RATE_LIMIT_ENABLED:
        return 0
    
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    key = (ip, endpoint)
    now = time.time()
    
    with _rate_lock:
        dq = _rate_hits.get(key)
        rate_max = _get_current_rate_limit()
        if not dq or len(dq) < rate_max:
            return 0
        
        oldest = dq[0]
        remaining = int(max(0, RATE_LIMIT_WINDOW_SEC - (now - oldest)))
        return remaining if remaining > 0 else 1


def get_rate_state(endpoint: str) -> Tuple[int, int]:
    """Return current (limit, remaining) without mutating counters.

    Remaining is computed after pruning expired timestamps.
    """
    rate_max = _get_current_rate_limit()
    if not RATE_LIMIT_ENABLED:
        return rate_max, rate_max
    
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    key = (ip, endpoint)
    now = time.time()
    
    with _rate_lock:
        dq = _rate_hits.get(key)
        if dq is None:
            return rate_max, rate_max
        
        cutoff = now - RATE_LIMIT_WINDOW_SEC
        # Prune expired entries (non-mutating semantics OK)
        while dq and dq[0] < cutoff:
            dq.popleft()
        
        remaining = max(0, rate_max - len(dq))
    
    return rate_max, remaining


# ----------------------------------------------------------------------------
# Caching System
# ----------------------------------------------------------------------------

_summary_cache: Dict[str, Tuple[float, Dict]] = {}
_summary_lock = threading.Lock()


def cache_get(key: str) -> Optional[Dict]:
    """Get cached value if still valid, None otherwise."""
    with _summary_lock:
        item = _summary_cache.get(key)
        if not item:
            return None
        
        timestamp, payload = item
        if time.time() - timestamp > AI_SUMMARY_CACHE_TTL:
            _summary_cache.pop(key, None)
            return None
        
        return payload


def cache_set(key: str, payload: Dict) -> None:
    """Set cached value with current timestamp."""
    with _summary_lock:
        _summary_cache[key] = (time.time(), payload)


def cache_clear() -> int:
    """Clear all cached entries and return count of cleared items."""
    with _summary_lock:
        count = len(_summary_cache)
        _summary_cache.clear()
        return count


def cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    with _summary_lock:
        now = time.time()
        valid_entries = sum(
            1 for ts, _ in _summary_cache.values()
            if now - ts <= AI_SUMMARY_CACHE_TTL
        )
        
        return {
            "total_entries": len(_summary_cache),
            "valid_entries": valid_entries,
            "expired_entries": len(_summary_cache) - valid_entries,
            "cache_ttl_seconds": AI_SUMMARY_CACHE_TTL,
        }

