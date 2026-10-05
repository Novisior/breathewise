"""Asks the configured AI model for personalised advice. Validates the JSON and retries once."""
import logging

from app.models import AdviceCore
from app.services import llm
from app.services.advice_prompt import SYSTEM_PROMPT, build_user_message, extract_json

log = logging.getLogger("breathewise.ai")


class AdviceAIError(Exception):
    """The AI provider could not be used (network, auth, rate limit, not configured...)."""


def ai_enabled() -> bool:
    return llm.is_configured()


async def _ask(messages: list[dict]) -> str:
    try:
        return await llm.chat(SYSTEM_PROMPT, messages)
    except Exception as e:  # log a short, secret-free reason only
        log.warning("AI call failed: %s", e if isinstance(e, llm.LLMError) else type(e).__name__)
        raise AdviceAIError(type(e).__name__) from None


def _parse(text: str) -> dict:
    """Raises ValueError (pydantic's ValidationError is a ValueError) if malformed."""
    return AdviceCore.model_validate(extract_json(text)).model_dump()


async def generate_ai_advice(ctx: dict) -> dict | None:
    """
    Returns validated advice (dict), or None if the model's output stayed
    invalid after ONE retry. Raises AdviceAIError if the provider itself failed.
    """
    messages = [{"role": "user", "content": build_user_message(ctx)}]

    text = await _ask(messages)
    try:
        return _parse(text)
    except ValueError as first_error:
        log.info("AI reply failed validation, retrying once")
        messages += [
            {"role": "assistant", "content": text or "(empty)"},
            {"role": "user", "content": (
                "Your last reply was not valid. Problem: "
                f"{str(first_error)[:300]}\n"
                "Reply again with ONLY the JSON object in the exact schema, nothing else.")},
        ]

    text = await _ask(messages)
    try:
        return _parse(text)
    except ValueError:
        log.warning("AI reply invalid after retry; falling back to rules")
        return None
