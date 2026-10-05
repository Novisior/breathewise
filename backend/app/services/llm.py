"""
One function, `chat()`, that talks to whichever AI provider you configured in .env:

  AI_PROVIDER=gemini             Google Gemini (free tier via Google AI Studio)
  AI_PROVIDER=groq               Groq (free tier; open models such as Llama)
  AI_PROVIDER=openai_compatible  anything OpenAI-compatible: xAI Grok, OpenRouter, ...
                                 (needs AI_BASE_URL and AI_MODEL)
  AI_PROVIDER=anthropic          Claude
  (unset / none)                 no AI: the app uses its rules-based advice

Uses plain httpx, so no provider SDK is needed. API keys travel only in request
headers and are never logged or put in URLs.
"""
import asyncio
import logging
import time
from urllib.parse import quote

import httpx

from app.config import settings
from app.services import llm_formats as fmt

log = logging.getLogger("breathewise.llm")

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
GROQ_BASE = "https://api.groq.com/openai/v1"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

# Defaults only: model names change often. Override with AI_MODEL in .env.
DEFAULT_MODELS = {
    "gemini": "gemini-3.5-flash",  # unverified guess: run check_ai.py to find a model your key can use
    "groq": "llama-3.3-70b-versatile",
    "anthropic": "claude-sonnet-5-5",
    "openai_compatible": "",  # you must set AI_MODEL
}
PROVIDERS = tuple(DEFAULT_MODELS)


class LLMError(Exception):
    """The AI provider could not be used. The message is safe to log (no secrets)."""


_http: httpx.AsyncClient | None = None
_gemini_ranked: list[str] = []  # auto-detected Gemini models, best first (cached per process)

TRANSIENT_STATUSES = {429, 500, 502, 503, 504}  # "try again / try another model" errors
RETRY_DELAY = 1.5   # seconds to wait before retrying a transient error
MAX_GEMINI_TRIES = 3
PER_TRY_TIMEOUT = 12.0  # auto-detect mode: give up on one model after this many seconds, try the next


def _client() -> httpx.AsyncClient:
    global _http
    if _http is None:
        _http = httpx.AsyncClient(timeout=settings.ai_timeout)
    return _http


async def aclose() -> None:
    """Close the shared HTTP client (call on shutdown, or before the event loop ends)."""
    global _http
    if _http is not None:
        await _http.aclose()
        _http = None


def model_name() -> str:
    return settings.ai_model or DEFAULT_MODELS.get(settings.ai_provider, "")


def is_configured() -> bool:
    p = settings.ai_provider
    if p not in PROVIDERS or not settings.ai_api_key:
        return False
    if p == "openai_compatible":
        return bool(settings.ai_base_url and model_name())
    return True


async def _get(url: str, headers: dict, params: dict | None = None) -> httpx.Response:
    try:
        return await _client().get(url, headers=headers, params=params)
    except httpx.TimeoutException:
        raise LLMError("timeout") from None
    except httpx.HTTPError:
        raise LLMError("network error") from None


async def list_gemini_models() -> list[str]:
    """Usable Gemini Flash model names for this key. Raises LLMError if the list call fails."""
    resp = await _get(f"{GEMINI_BASE}/models", {"x-goog-api-key": settings.ai_api_key},
                      {"pageSize": 200})
    return fmt.usable_gemini_models(_json(resp))


async def _gemini_models(force: bool = False) -> list[str]:
    """AI_MODEL if set; otherwise auto-detect once, best model first (default if detection fails)."""
    global _gemini_ranked
    if settings.ai_model:
        return [settings.ai_model]
    if not _gemini_ranked or force:
        ranked: list[str] = []
        try:
            resp = await _get(f"{GEMINI_BASE}/models", {"x-goog-api-key": settings.ai_api_key},
                              {"pageSize": 200})
            ranked = fmt.rank_gemini_models(_json(resp))
        except LLMError as e:
            log.warning("Could not auto-detect a Gemini model (%s); using default", e)
        _gemini_ranked = ranked or [DEFAULT_MODELS["gemini"]]
        log.info("Gemini models (best first): %s", ", ".join(_gemini_ranked[:4]))
    return _gemini_ranked


def _demote(model: str) -> None:
    """A model that was slow/busy goes to the back of the line for the rest of this process."""
    if model in _gemini_ranked and len(_gemini_ranked) > 1:
        _gemini_ranked.remove(model)
        _gemini_ranked.append(model)


async def _gemini_generate(system: str, messages: list[dict]) -> httpx.Response:
    """
    Call Gemini with resilience. Total time is capped by AI_TIMEOUT_SECONDS.
      * 404 on an auto-detected model -> re-detect once (models get retired)
      * 429/5xx ("busy") or a slow answer -> try the next-best model, and demote the bad one
        (with a fixed AI_MODEL: retry the same model once on busy errors; never on timeouts)
    """
    headers = {"x-goog-api-key": settings.ai_api_key}
    body = fmt.build_gemini(system, messages)
    explicit = bool(settings.ai_model)
    deadline = time.monotonic() + settings.ai_timeout

    def url(model: str) -> str:
        return f"{GEMINI_BASE}/models/{quote(model, safe='')}:generateContent"

    models = await _gemini_models()
    candidates = [models[0], models[0]] if explicit else list(models[:MAX_GEMINI_TRIES])
    rediscovered = False
    i = 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining < 1:
            raise LLMError("timeout")
        per_try = remaining if explicit else min(PER_TRY_TIMEOUT, remaining)
        model = candidates[i]
        try:
            resp = await _post(url(model), headers, body, timeout=per_try)
        except LLMError as e:
            if str(e) == "timeout" and not explicit and i < len(candidates) - 1:
                log.warning("Gemini model %s too slow; trying the next one", model)
                _demote(model)
                i += 1
                continue
            raise
        if resp.status_code == 404 and not explicit and not rediscovered:
            rediscovered = True
            candidates = (await _gemini_models(force=True))[:MAX_GEMINI_TRIES]
            i = 0
            continue
        if resp.status_code in TRANSIENT_STATUSES and i < len(candidates) - 1:
            log.warning("Gemini model %s busy (HTTP %s); trying again", model, resp.status_code)
            if not explicit:
                _demote(model)
            await asyncio.sleep(RETRY_DELAY)
            i += 1
            continue
        return resp


def status() -> dict:
    """Safe-to-show AI status (never includes the key). `problem` explains what to fix."""
    p = settings.ai_provider
    problem = None
    if p == "none":
        problem = "AI_PROVIDER is not set, so rules-only advice is used."
    elif p not in PROVIDERS:
        problem = f"AI_PROVIDER '{p}' is not valid. Use one of: {', '.join(PROVIDERS)}."
    elif not settings.ai_api_key:
        problem = "AI_API_KEY is empty."
    elif p == "openai_compatible" and not (settings.ai_base_url and model_name()):
        problem = "openai_compatible needs both AI_BASE_URL and AI_MODEL."
    shown = (settings.ai_model or (_gemini_ranked[0] if _gemini_ranked else "auto-detect")) if p == "gemini" else (model_name() or None)
    return {"provider": p, "model": shown,
            "configured": is_configured(), "problem": problem}


async def _post(url: str, headers: dict, body: dict, timeout: float | None = None) -> httpx.Response:
    extra = {} if timeout is None else {"timeout": timeout}
    try:
        return await _client().post(url, headers=headers, json=body, **extra)
    except httpx.TimeoutException:
        raise LLMError("timeout") from None
    except httpx.HTTPError:
        raise LLMError("network error") from None


def _json(resp: httpx.Response) -> dict:
    if resp.status_code >= 400:
        # Status code only: error bodies can echo request details.
        hint = " (model not found: check AI_MODEL, run check_ai.py)" if resp.status_code == 404 else ""
        raise LLMError(f"HTTP {resp.status_code}{hint}")
    try:
        data = resp.json()
    except ValueError:
        raise LLMError("response was not JSON") from None
    if not isinstance(data, dict):
        raise LLMError("unexpected response format")
    return data


async def chat(system: str, messages: list[dict]) -> str:
    """Send a conversation to the configured provider and return the reply text."""
    if not is_configured():
        raise LLMError("AI provider is not configured")
    provider, model, key = settings.ai_provider, model_name(), settings.ai_api_key  # model: non-Gemini

    try:
        if provider == "gemini":
            return fmt.parse_gemini(_json(await _gemini_generate(system, messages)))

        if provider == "anthropic":
            headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
            resp = await _post(ANTHROPIC_URL, headers, fmt.build_anthropic(model, system, messages))
            return fmt.parse_anthropic(_json(resp))

        # groq / openai_compatible share the OpenAI chat-completions format.
        base = GROQ_BASE if provider == "groq" else settings.ai_base_url.rstrip("/")
        url, headers = f"{base}/chat/completions", {"Authorization": f"Bearer {key}"}
        resp = await _post(url, headers, fmt.build_openai(model, system, messages, json_mode=True))
        if resp.status_code == 400:  # some providers/models reject JSON mode: retry without it
            resp = await _post(url, headers, fmt.build_openai(model, system, messages, json_mode=False))
        if resp.status_code in TRANSIENT_STATUSES:  # provider busy: one short retry
            await asyncio.sleep(RETRY_DELAY)
            resp = await _post(url, headers, fmt.build_openai(model, system, messages, json_mode=True))
        return fmt.parse_openai(_json(resp))

    except LLMError:
        raise
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        raise LLMError("unexpected response format") from None
