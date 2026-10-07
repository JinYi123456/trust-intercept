"""LLM access for TRUST//INTERCEPT.

Provider policy (blueprint): **Claude (Sonnet) primary; Gemini as fallback** —
a second provider stays wired in case of rate limits during judging. If no key
is configured (or both providers fail), a deterministic English template
engine keeps the demo alive: verdicts still carry cues, confidence bands and
uncertainty notes, they are just less prose-rich.

All prompts, reasoning steps, tool outputs and responses are strictly in
ENGLISH — every prompt template instructs the model to answer in English and
the client asserts it.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

import httpx

from backend.agent.prompts import load_prompt
from backend.config import get_settings


class LlmUnavailable(RuntimeError):
    """Raised when no LLM provider can serve a completion."""


def _strip_code_fence(text: str) -> str:
    """Models sometimes wrap JSON in ```json fences; unwrap before parsing."""
    trimmed = text.strip()
    match = re.search(r"```(?:json)?\s*(.+?)\s*```", trimmed, re.DOTALL)
    return match.group(1).strip() if match else trimmed


def _parse_json_object(text: str) -> Optional[dict[str, Any]]:
    try:
        parsed = json.loads(_strip_code_fence(text))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _english_only(text: str) -> str:
    """Last-resort guard: if the model ignored the English instruction, say so."""
    # A cheap heuristic: most non-English text contains no ASCII letters at all.
    if text and not re.search(r"[A-Za-z]", text):
        return "(The model did not respond in English; treating the response as unusable.)"
    return text


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


def _call_anthropic(prompt: str, system: str) -> str:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise LlmUnavailable("No ANTHROPIC_API_KEY configured.")
    body = {
        "model": settings.anthropic_model,
        "max_tokens": settings.llm_max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        response = httpx.post(
            settings.anthropic_base_url,
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": settings.anthropic_version,
                "content-type": "application/json",
            },
            json=body,
            timeout=settings.llm_timeout_seconds,
        )
    except Exception as exc:
        raise LlmUnavailable(f"Anthropic request failed: {type(exc).__name__}: {exc}") from exc
    if response.status_code != 200:
        raise LlmUnavailable(f"Anthropic returned HTTP {response.status_code}.")
    try:
        text = response.json()["content"][0]["text"]
    except Exception as exc:
        raise LlmUnavailable(f"Could not parse the Anthropic response: {exc}") from exc
    return _english_only(text)


def _call_gemini(prompt: str, system: str) -> str:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise LlmUnavailable("No GEMINI_API_KEY configured.")
    url = (
        f"{settings.gemini_base_url}/{settings.gemini_model}:generateContent"
        f"?key={settings.gemini_api_key}"
    )
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": settings.llm_max_tokens},
    }
    try:
        response = httpx.post(url, json=body, timeout=settings.llm_timeout_seconds)
    except Exception as exc:
        raise LlmUnavailable(f"Gemini request failed: {type(exc).__name__}: {exc}") from exc
    if response.status_code != 200:
        raise LlmUnavailable(f"Gemini returned HTTP {response.status_code}.")
    try:
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:
        raise LlmUnavailable(f"Could not parse the Gemini response: {exc}") from exc
    return _english_only(text)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def llm_status() -> dict[str, Any]:
    """Which providers are configured — shown on /health for demo prep."""
    settings = get_settings()
    return {
        "provider_setting": settings.llm_provider,
        "anthropic_configured": bool(settings.anthropic_api_key),
        "anthropic_model": settings.anthropic_model,
        "gemini_configured": bool(settings.gemini_api_key),
        "gemini_model": settings.gemini_model,
        "template_mode": settings.llm_provider == "none"
        or not (settings.anthropic_api_key or settings.gemini_api_key),
    }


def generate(
    prompt_name: str,
    context: dict[str, Any],
    *,
    system: Optional[str] = None,
) -> dict[str, Any]:
    """Render the named prompt template with ``context`` and get structured JSON.

    Returns a dict that always contains ``raw_text`` (the model's full English
    response) plus whatever JSON object the model produced (parsed from its
    answer). Raises :class:`LlmUnavailable` only when template mode is also
    impossible — callers are expected to fall back to deterministic logic.
    """
    settings = get_settings()
    prompt = load_prompt(prompt_name, context)
    system = system or (
        "You are TRUST//INTERCEPT, an agentic scam-defence and decision-safety assistant. You NEVER decide or execute "
        "actions yourself; you only investigate evidence, challenge conclusions, and propose safe next steps for a "
        "human to approve. You always answer in English. When asked for JSON, "
        "reply with ONLY the JSON object and nothing else."
    )

    errors: list[str] = []
    order: list[str]
    if settings.llm_provider == "anthropic":
        order = ["anthropic"]
    elif settings.llm_provider == "gemini":
        order = ["gemini"]
    elif settings.llm_provider == "none":
        order = []
    else:  # auto: Claude primary, Gemini fallback
        order = ["anthropic", "gemini"]

    raw_text = ""
    used_provider = ""
    for provider in order:
        try:
            raw_text = _call_anthropic(prompt, system) if provider == "anthropic" else _call_gemini(prompt, system)
            used_provider = provider
            break
        except LlmUnavailable as exc:
            errors.append(f"{provider}: {exc}")

    if not raw_text:
        raise LlmUnavailable(
            "No LLM provider available (" + "; ".join(errors) + ")"
            if errors
            else "LLM usage is disabled (LLM_PROVIDER=none)."
        )

    parsed = _parse_json_object(raw_text) or {}
    return {"provider": used_provider, "raw_text": raw_text, **parsed}
