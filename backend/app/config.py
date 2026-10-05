"""Settings loaded from environment variables (and backend/.env if present)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # reads backend/.env when running from the backend folder


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    # AI provider: gemini | groq | openai_compatible | anthropic | none (rules only)
    ai_provider: str = os.getenv("AI_PROVIDER", "").strip().lower() or "none"
    ai_api_key: str = os.getenv("AI_API_KEY", "").strip()  # never log this
    ai_model: str = os.getenv("AI_MODEL", "").strip()      # optional: provider default if empty
    ai_base_url: str = os.getenv("AI_BASE_URL", "").strip()  # only for openai_compatible
    cors_origins: tuple = tuple(
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if o.strip()
    )
    http_timeout: int = _int("HTTP_TIMEOUT_SECONDS", 10)
    ai_timeout: int = _int("AI_TIMEOUT_SECONDS", 20)
    air_cache_ttl: int = _int("AIR_CACHE_TTL_SECONDS", 900)
    advice_cache_ttl: int = _int("ADVICE_CACHE_TTL_SECONDS", 3600)
    geocode_cache_ttl: int = 24 * 3600


settings = Settings()
