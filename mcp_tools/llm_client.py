"""
mcp_tools/llm_client.py — Unified LLM Provider Abstraction
Swap provider via settings.py only. Never hardcode model/URL in agent files.

Supported providers (all free tier):
  groq     → llama-3.3-70b-versatile   (OpenAI-compatible)
  gemini   → gemini-2.5-flash-lite     (Google GenAI SDK)
  mistral  → mistral-small-latest      (OpenAI-compatible)
"""
from __future__ import annotations

import json
import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    GROQ = "groq"
    GEMINI = "gemini"
    MISTRAL = "mistral"


# ---------------------------------------------------------------------------
# Rate-limit token buckets (in-process, single-worker simplification)
# For multi-worker deploy: back with Redis instead.
# ---------------------------------------------------------------------------
class _RateLimiter:
    """Simple sliding-window rate limiter for free-tier quotas."""

    def __init__(self, rpm: int):
        self._rpm = rpm
        self._window: List[float] = []  # timestamps of recent calls

    def acquire(self) -> None:
        """Block until a request slot is available."""
        now = time.monotonic()
        # Drop timestamps older than 60 seconds
        self._window = [t for t in self._window if now - t < 60]
        if len(self._window) >= self._rpm:
            sleep_for = 60 - (now - self._window[0]) + 0.1
            logger.warning(
                json.dumps({"event": "rate_limit_wait", "sleep_seconds": float(int(sleep_for * 10) / 10.0)})
            )
            time.sleep(max(sleep_for, 0))
        self._window.append(time.monotonic())


_rate_limiters: Dict[str, _RateLimiter] = {}


def _get_limiter(provider: str, rpm: int) -> _RateLimiter:
    if provider not in _rate_limiters:
        _rate_limiters[provider] = _RateLimiter(rpm)
    return _rate_limiters[provider]


# ---------------------------------------------------------------------------
# Groq / Mistral  (OpenAI-compatible  — no extra SDK needed)
# ---------------------------------------------------------------------------
def _call_openai_compat(
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> str:
    """
    Generic caller for any OpenAI-compatible endpoint (Groq, Mistral).
    Returns the text of the first choice.
    """
    import httpx

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    resp = httpx.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Gemini  (Google GenAI SDK)
# ---------------------------------------------------------------------------
def _call_gemini(
    api_key: str,
    model: str,
    prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> str:
    """
    Calls Google Gemini via the google-generativeai SDK.
    Converts chat-style messages to a single prompt string for simplicity.
    """
    import google.generativeai as genai  # pip install google-generativeai

    genai.configure(api_key=api_key)
    gen_model = genai.GenerativeModel(model_name=model)
    response = gen_model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=temperature, max_output_tokens=max_tokens
        ),
    )
    return response.text


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
def call_llm(
    provider: LLMProvider,
    messages: List[Dict[str, str]],   # [{"role": "system"|"user", "content": "..."}]
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> str:
    """
    Route an LLM call to the correct provider.
    All agent files call THIS function — never the provider SDKs directly.

    Args:
        provider:    LLMProvider enum value
        messages:    OpenAI-style message list
        temperature: Sampling temperature
        max_tokens:  Max output tokens

    Returns:
        Str — raw model output (agent is responsible for parsing JSON if needed)

    Raises:
        ValueError if provider unknown
        httpx.HTTPStatusError / google.api_core.exceptions.* on API errors
    """
    from config.settings import settings

    # Flatten messages to a single prompt for Gemini
    def _flatten(msgs: List[Dict[str, str]]) -> str:
        return "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in msgs)

    logger.info(json.dumps({"event": "llm_call", "provider": provider.value, "msg_count": len(messages)}))

    if provider == LLMProvider.GROQ:
        limiter = _get_limiter("groq", settings.GROQ_RPM_LIMIT)
        
        models_to_try = [
            settings.GROQ_MODEL,
            getattr(settings, "GROQ_FALLBACK_1", None),
            getattr(settings, "GROQ_FALLBACK_2", None)
        ]
        # Filter out None values in case fallbacks aren't defined
        models_to_try = [m for m in models_to_try if m]

        last_exc = None
        for model in models_to_try:
            try:
                limiter.acquire()
                logger.info(json.dumps({"event": "llm_call_attempt", "provider": "groq", "model": model}))
                return _call_openai_compat(
                    base_url=settings.GROQ_BASE_URL,
                    api_key=settings.GROQ_API_KEY,
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as exc:
                last_exc = exc
                logger.warning(json.dumps({
                    "event": "llm_call_fallback",
                    "provider": "groq",
                    "failed_model": model,
                    "error": str(exc)
                }))
                continue
        
        # If all models failed, raise the last exception
        if isinstance(last_exc, Exception):
            raise last_exc
        raise ValueError("No Groq models available to call")

    elif provider == LLMProvider.GEMINI:
        # Gemini quota is by day — no in-process RPM guard needed beyond basic tracking
        return _call_gemini(
            api_key=settings.GOOGLE_API_KEY,
            model=settings.GEMINI_MODEL,
            prompt=_flatten(messages),
            temperature=temperature,
            max_tokens=max_tokens,
        )

    elif provider == LLMProvider.MISTRAL:
        limiter = _get_limiter("mistral", 60)  # Mistral free tier ~60 rpm
        limiter.acquire()
        return _call_openai_compat(
            base_url=settings.MISTRAL_BASE_URL,
            api_key=settings.MISTRAL_API_KEY,
            model=settings.MISTRAL_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

