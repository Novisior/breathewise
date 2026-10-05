"""
Request/response shapes for each LLM provider. Pure Python (no network, no httpx),
so the shapes can be unit-tested offline.

messages = [{"role": "user" | "assistant", "content": "..."}]
"""
from __future__ import annotations

import re

TEMPERATURE = 0.2        # low = steadier, more consistent advice
MAX_OUTPUT_TOKENS = 4096  # generous: some models spend tokens "thinking" first


def build_gemini(system: str, messages: list[dict]) -> dict:
    return {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [
            {"role": "model" if m["role"] == "assistant" else "user",
             "parts": [{"text": m["content"]}]}
            for m in messages
        ],
        "generationConfig": {
            "responseMimeType": "application/json",  # ask Gemini for JSON only
            "temperature": TEMPERATURE,
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
        },
    }


def parse_gemini(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        raise ValueError("Gemini returned no candidates (possibly blocked).")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts
                   if isinstance(p, dict) and not p.get("thought"))


def build_openai(model: str, system: str, messages: list[dict], json_mode: bool = True) -> dict:
    """OpenAI-compatible chat completions body (Groq, xAI Grok, OpenRouter, OpenAI...)."""
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}] + list(messages),
        "temperature": TEMPERATURE,
        "max_tokens": MAX_OUTPUT_TOKENS,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    return body


def parse_openai(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("No choices in response.")
    return (choices[0].get("message") or {}).get("content") or ""


def build_anthropic(model: str, system: str, messages: list[dict]) -> dict:
    return {"model": model, "max_tokens": 1200, "system": system, "messages": list(messages)}


def parse_anthropic(data: dict) -> str:
    return "".join(b.get("text", "") for b in data.get("content") or []
                   if isinstance(b, dict) and b.get("type") == "text")


# ---------------- Gemini model discovery ----------------
# Google retires models every few months, so instead of trusting a hardcoded name
# we ask the API which models this key can use and pick the best Flash model.

_NOT_TEXT_CHAT = ("image", "tts", "audio", "live", "native", "embedding", "robotics",
                  "computer", "veo", "imagen", "lyria", "gemma", "aqa", "thinking")
_VERSION = re.compile(r"^gemini-(\d+(?:\.\d+)*)-")


def usable_gemini_models(data: dict) -> list[str]:
    """Names of Gemini Flash models that support text generation, from a models.list response."""
    out = []
    for m in data.get("models") or []:
        name = str(m.get("name") or "").removeprefix("models/")
        if "generateContent" not in (m.get("supportedGenerationMethods") or []):
            continue
        if not name.startswith("gemini-") or "flash" not in name:
            continue
        if any(bad in name for bad in _NOT_TEXT_CHAT):
            continue
        out.append(name)
    return out


def _rank(name: str) -> tuple:
    m = _VERSION.match(name)
    version = tuple(int(x) for x in m.group(1).split(".")) if m else (0,)
    stable = not any(t in name for t in ("preview", "exp"))
    return (stable, version, "lite" not in name)


def rank_names(names: list[str]) -> list[str]:
    """Order model names best first: the always-current alias, then newest stable non-lite, etc."""
    ranked = sorted(names, key=_rank, reverse=True)
    if "gemini-flash-latest" in ranked:
        ranked.remove("gemini-flash-latest")
        ranked.insert(0, "gemini-flash-latest")
    return ranked


def rank_gemini_models(data: dict) -> list[str]:
    return rank_names(usable_gemini_models(data))


def pick_gemini_model(data: dict) -> str | None:
    ranked = rank_gemini_models(data)
    return ranked[0] if ranked else None
