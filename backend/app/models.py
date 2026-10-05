"""Pydantic models: they validate and document what our API accepts and returns."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.text_utils import trim_sentences


class Location(BaseModel):
    latitude: float
    longitude: float
    timezone: str | None = None


class Pollutants(BaseModel):
    """Latest readings. ug/m3 for all, except `co` which is mg/m3."""
    pm2_5: float | None = None
    pm10: float | None = None
    no2: float | None = None
    o3: float | None = None
    so2: float | None = None
    co: float | None = None


class Weather(BaseModel):
    temperature_c: float | None = None
    humidity_pct: float | None = None


class HourlyPoint(BaseModel):
    time: str            # local time at the location, e.g. "2026-10-01T14:00"
    aqi: int
    category: str        # good | satisfactory | moderate | poor | very_poor | severe
    dominant: str
    aqi_instant: int | None = None        # unaveraged, for charts / best-time planner
    category_instant: str | None = None
    pm2_5: float | None = None


class AirResponse(BaseModel):
    location: Location
    observed_at: str
    updated_at: str      # when WE fetched it (UTC ISO) -> shown as "last updated"
    aqi: int
    category: str
    category_label: str
    dominant: str
    aqi_instant: int | None = None        # "right now" AQI without 24h averaging
    category_instant: str | None = None
    approximate: bool    # True if some pollutant lacked enough history for CPCB averaging
    pollutants: Pollutants
    sub_indices: dict[str, int]
    weather: Weather
    forecast: list[HourlyPoint]


class GeocodeResult(BaseModel):
    name: str
    admin1: str | None = None
    country: str | None = None
    country_code: str | None = None
    latitude: float
    longitude: float
    label: str


class GeocodeResponse(BaseModel):
    results: list[GeocodeResult]


# ----------------------------------------------------------------------
# Advice: request
# ----------------------------------------------------------------------
Category = Literal["good", "satisfactory", "moderate", "poor", "very_poor", "severe"]
PollutantKey = Literal["pm2_5", "pm10", "no2", "o3", "so2", "co"]
Condition = Literal["asthma", "copd", "heart_disease", "diabetes", "pregnancy", "none"]
Routine = Literal[
    "outdoor_exercise", "commute_two_wheeler", "commute_walk",
    "commute_public_transport", "commute_car", "outdoor_work", "mostly_indoors",
]


class UserProfile(BaseModel):
    age_group: Literal["child", "teen", "adult", "senior"]
    conditions: list[Condition] = Field(default_factory=list, max_length=6)
    routine: list[Routine] = Field(default_factory=list, max_length=7)


class ForecastPointIn(BaseModel):
    # Every field is a strict enum / number / fixed-format string, so nothing
    # free-form from the client can reach the AI prompt.
    time: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")
    aqi: int = Field(ge=0, le=500)
    category: Category | None = None
    dominant: PollutantKey | None = None
    aqi_instant: int | None = Field(default=None, ge=0, le=500)
    category_instant: Category | None = None
    pm2_5: float | None = Field(default=None, ge=0, le=5000)


class AdviceAirIn(BaseModel):
    """The /api/air response (extra fields are ignored). Categories are recomputed server-side."""
    aqi: int = Field(ge=0, le=500)
    category: Category | None = None
    dominant: PollutantKey | None = None
    aqi_instant: int | None = Field(default=None, ge=0, le=500)
    category_instant: Category | None = None
    pollutants: Pollutants = Field(default_factory=Pollutants)
    forecast: list[ForecastPointIn] = Field(default_factory=list, max_length=72)


class AdviceRequest(BaseModel):
    profile: UserProfile
    language: Literal["en", "hi"] = "en"
    air: AdviceAirIn
    # False = instant rules-based answer (still returns cached AI advice if we have it).
    # Lets the app show advice immediately, then ask again with use_ai=true to upgrade it.
    use_ai: bool = True


# ----------------------------------------------------------------------
# Advice: what the AI must return, and what we return to the app
# ----------------------------------------------------------------------
_RISK_ALIASES = {"low": "Low", "moderate": "Moderate", "high": "High",
                 "very high": "Very High", "very_high": "Very High", "veryhigh": "Very High"}
_MASK_ALIASES = {"n95": "n95", "kn95": "n95", "ffp2": "n95", "surgical": "surgical",
                 "surgicalmask": "surgical", "none": "none", "nomask": "none", "no": "none"}


class AdviceCore(BaseModel):
    """The JSON schema Claude must produce (validated, then safety-checked in code)."""
    model_config = ConfigDict(extra="ignore")

    risk_level: Literal["Low", "Moderate", "High", "Very High"]
    summary: str = Field(min_length=1, max_length=800)
    do: list[str] = Field(min_length=1, max_length=8)
    avoid: list[str] = Field(default_factory=list, max_length=8)
    mask: Literal["none", "surgical", "n95"]
    exercise_advice: str = Field(min_length=1, max_length=800)
    best_time_window: str = Field(min_length=1, max_length=400)

    @field_validator("risk_level", mode="before")
    @classmethod
    def _norm_risk(cls, v):
        if isinstance(v, str) and v.strip().lower() in _RISK_ALIASES:
            return _RISK_ALIASES[v.strip().lower()]
        raise ValueError("risk_level must be Low, Moderate, High or Very High")

    @field_validator("mask", mode="before")
    @classmethod
    def _norm_mask(cls, v):
        key = str(v).strip().lower().replace(" ", "").replace("-", "")
        if key in _MASK_ALIASES:
            return _MASK_ALIASES[key]
        raise ValueError("mask must be none, surgical or n95")

    @field_validator("summary", "exercise_advice", "best_time_window")
    @classmethod
    def _two_sentences(cls, v: str) -> str:
        return trim_sentences(v.strip(), 2)

    @field_validator("do", "avoid")
    @classmethod
    def _clean_items(cls, v: list[str]) -> list[str]:
        return [trim_sentences(s.strip(), 2) for s in v if isinstance(s, str) and s.strip()]


class AdviceResponse(AdviceCore):
    disclaimer: str                       # fixed text, added by code (never by the model)
    source: Literal["ai", "rules"]
    language: Literal["en", "hi"]
    # Why the rules fallback was used (None when the AI answered). Safe to show: no secrets.
    fallback_reason: Literal[
        "ai_skipped", "ai_not_configured", "ai_error", "ai_cooldown", "ai_invalid_output",
        "ai_rejected_by_safety"
    ] | None = None
