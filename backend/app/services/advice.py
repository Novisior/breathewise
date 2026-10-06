
import logging
import time

from app.cache import TTLCache
from app.config import settings
from app.models import AdviceRequest
from app.services import advice_ai
from app.services import advice_rules as rules

log = logging.getLogger("breathewise.advice")

AI_COOLDOWN_SECONDS = 60  # after an API failure, skip the AI briefly instead of timing out every request

advice_cache = TTLCache(settings.advice_cache_ttl)
_cooldown_until = 0.0


def reset_state() -> None:
    """Clear cache and cooldown (used by tests)."""
    global _cooldown_until
    advice_cache.clear()
    _cooldown_until = 0.0


async def get_advice(req: AdviceRequest) -> dict:
    global _cooldown_until
    ctx = rules.build_context(req.profile.model_dump(), req.language, req.air.model_dump())
    rules_advice = rules.rules_core(ctx)

    core, source, reason = rules_advice, "rules", None
    key = rules.cache_key(ctx)

    cached = advice_cache.get(key)
    if cached is not None:
        core, source = rules.with_fresh_window(cached, ctx), "ai"
    elif not req.use_ai:
        reason = "ai_skipped"
    elif not advice_ai.ai_enabled():
        reason = "ai_not_configured"
    elif time.monotonic() < _cooldown_until:
        reason = "ai_cooldown"
    else:
        try:
            ai_core = await advice_ai.generate_ai_advice(ctx)
        except advice_ai.AdviceAIError:
            _cooldown_until = time.monotonic() + AI_COOLDOWN_SECONDS
            reason = "ai_error"
        else:
            if ai_core is None:
                reason = "ai_invalid_output"
            else:
                checked = rules.enforce_safety(ai_core, ctx, rules_advice)
                if checked is None:
                    log.warning("AI advice rejected by safety checks; using rules")
                    reason = "ai_rejected_by_safety"
                else:
                    advice_cache.set(key, checked)
                    core, source = checked, "ai"

    return {
        **core,
        "disclaimer": rules.DISCLAIMER[ctx["language"]],  
        "source": source,
        "language": ctx["language"],
        "fallback_reason": reason if source == "rules" else None,
    }
