"""Minimal xAI (Grok) client wrapper.

This module keeps the integration optional:
 - If env var XAI_API_KEY is not present, ai_enabled() returns False and
   grok_chat will raise RuntimeError('ai_disabled').
 - On network / API errors we return a structured error dict instead of raising.

We intentionally avoid adding a hard dependency on any heavyweight SDK;
plain HTTP via `requests` keeps the surface small and easier to vendor.
"""
from __future__ import annotations

import os
import json
import logging
from typing import Iterable, Dict, Any

try:  # Local, lightweight dep – added to backend/requirements.txt
    import requests  # type: ignore
except ImportError:  # pragma: no cover - defensive
    requests = None  # type: ignore

logger = logging.getLogger(__name__)

XAI_API_KEY = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
XAI_BASE_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
XAI_DEFAULT_MODEL = os.getenv("XAI_MODEL", "grok-2-latest")


def ai_enabled() -> bool:
    """Return True if the integration is usable (key + requests installed)."""
    # Exclude known dummy/test keys that won't work with the real API
    if not XAI_API_KEY or not requests:
        return False
    # Filter out dummy keys used in tests
    dummy_keys = {"TU_KEY", "test", "dummy", "fake"}
    if XAI_API_KEY.strip() in dummy_keys:
        return False
    return True


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json",
    }


def grok_chat(messages: Iterable[Dict[str, str]], *, model: str | None = None, max_output_tokens: int | None = None, temperature: float | None = None) -> Dict[str, Any]:
    """Call Grok chat completion style endpoint.

    Parameters
    ----------
    messages: list of {role: "system"|"user"|"assistant", content: str}
    model: override default model (env XAI_MODEL or grok-2-latest)
    max_output_tokens: optional generation cap
    temperature: optional sampling temperature

    Returns a dict with keys:
      ok: bool
      content: str | None
      raw: original response (optional)
      error: str (when ok is False)
    """
    if not ai_enabled():  # Fast fail to avoid network attempt
        raise RuntimeError("ai_disabled")
    if requests is None:  # pragma: no cover
        raise RuntimeError("requests_not_installed")

    url = f"{XAI_BASE_URL.rstrip('/')}/chat/completions"
    payload: Dict[str, Any] = {
        "model": model or XAI_DEFAULT_MODEL,
        "messages": list(messages),
    }
    if max_output_tokens is not None:
        payload["max_output_tokens"] = max_output_tokens
    if temperature is not None:
        payload["temperature"] = temperature

    try:
        resp = requests.post(url, headers=_headers(), data=json.dumps(payload), timeout=60)  # type: ignore[arg-type]
    except requests.RequestException as exc:  # type: ignore[attr-defined]
        logger.warning("xAI network error: %s", exc)
        return {"ok": False, "error": "network_error", "detail": str(exc)}

    if resp.status_code >= 400:
        try:
            data = resp.json()
        except ValueError:
            data = {"error": resp.text}
        logger.warning("xAI API error %s: %s", resp.status_code, data)
        return {"ok": False, "error": "api_error", "status": resp.status_code, "detail": data}
    try:
        data = resp.json()
    except ValueError as exc:
        return {"ok": False, "error": "decode_error", "detail": str(exc)}

    # Expected OpenAI-like structure
    content = None
    choices = data.get("choices") or []
    if choices:
        content = (choices[0].get("message") or {}).get("content")

    return {"ok": True, "content": content, "raw": data}


__all__ = ["grok_chat", "ai_enabled"]
