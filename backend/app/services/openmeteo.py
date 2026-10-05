"""Thin async wrappers around the free Open-Meteo APIs (no API key needed)."""
import httpx

from app.services.air_builder import AIR_VARIABLES, FORECAST_HOURS, PAST_HOURS

AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"


class UpstreamError(Exception):
    """An external service failed. The message is safe to show to users."""


async def _get_json(client: httpx.AsyncClient, url: str, params: dict) -> dict:
    try:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
    except httpx.TimeoutException:
        raise UpstreamError("The air quality service timed out.") from None
    except httpx.HTTPStatusError as e:
        raise UpstreamError(f"The air quality service returned an error ({e.response.status_code}).") from None
    except (httpx.HTTPError, ValueError):
        raise UpstreamError("Could not reach the air quality service.") from None


async def fetch_air(client: httpx.AsyncClient, lat: float, lon: float) -> dict:
    return await _get_json(client, AIR_URL, {
        "latitude": lat,
        "longitude": lon,
        "current": AIR_VARIABLES,
        "hourly": AIR_VARIABLES,
        "past_hours": PAST_HOURS,
        "forecast_hours": FORECAST_HOURS,
        "timezone": "auto",
    })


async def fetch_weather(client: httpx.AsyncClient, lat: float, lon: float) -> dict:
    return await _get_json(client, WEATHER_URL, {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m",
        "timezone": "auto",
    })


async def search_city(client: httpx.AsyncClient, query: str, lang: str = "en") -> dict:
    return await _get_json(client, GEOCODE_URL, {
        "name": query, "count": 8, "language": lang, "format": "json",
    })
