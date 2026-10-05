"""Endpoint tests. Open-Meteo is replaced by fake functions: no network needed."""
import pytest
from fastapi.testclient import TestClient

from app import main
from app.services import openmeteo
from tests.helpers import WEATHER_JSON, make_air_json


@pytest.fixture(autouse=True)
def clean_caches():
    main.air_cache.clear()
    main.geocode_cache.clear()


@pytest.fixture
def client():
    with TestClient(main.app) as c:  # "with" runs the startup/shutdown lifespan
        yield c


def fake_upstream(monkeypatch, air_error=False, weather_error=False):
    calls = {"air": 0}

    async def fake_air(http, lat, lon):
        calls["air"] += 1
        if air_error:
            raise openmeteo.UpstreamError("The air quality service timed out.")
        return make_air_json()

    async def fake_weather(http, lat, lon):
        if weather_error:
            raise openmeteo.UpstreamError("weather down")
        return WEATHER_JSON

    monkeypatch.setattr(openmeteo, "fetch_air", fake_air)
    monkeypatch.setattr(openmeteo, "fetch_weather", fake_weather)
    return calls


def test_air_happy_path(client, monkeypatch):
    fake_upstream(monkeypatch)
    r = client.get("/api/air", params={"lat": 28.61, "lon": 77.21})
    assert r.status_code == 200
    body = r.json()
    assert body["aqi"] == 232 and body["category"] == "poor"
    assert len(body["forecast"]) == 48
    assert body["weather"]["temperature_c"] == 31.4


def test_air_is_cached_for_nearby_coordinates(client, monkeypatch):
    calls = fake_upstream(monkeypatch)
    client.get("/api/air", params={"lat": 28.6101, "lon": 77.2101})
    client.get("/api/air", params={"lat": 28.6102, "lon": 77.2099})
    assert calls["air"] == 1


def test_weather_failure_is_tolerated(client, monkeypatch):
    fake_upstream(monkeypatch, weather_error=True)
    r = client.get("/api/air", params={"lat": 28.61, "lon": 77.21})
    assert r.status_code == 200
    assert r.json()["weather"]["temperature_c"] is None


def test_air_failure_returns_502_with_safe_message(client, monkeypatch):
    fake_upstream(monkeypatch, air_error=True)
    r = client.get("/api/air", params={"lat": 28.61, "lon": 77.21})
    assert r.status_code == 502
    assert "timed out" in r.json()["detail"]


@pytest.mark.parametrize("lat,lon", [(91, 77), (-91, 77), (28, 181), (28, -181)])
def test_out_of_range_coordinates_rejected(client, lat, lon):
    assert client.get("/api/air", params={"lat": lat, "lon": lon}).status_code == 422


def test_missing_coordinates_rejected(client):
    assert client.get("/api/air").status_code == 422


def test_geocode_happy_path_and_validation(client, monkeypatch):
    async def fake_search(http, q, lang):
        return {"results": [{"name": "Delhi", "admin1": "Delhi", "country": "India",
                             "country_code": "IN", "latitude": 28.65, "longitude": 77.23}]}
    monkeypatch.setattr(openmeteo, "search_city", fake_search)

    r = client.get("/api/geocode", params={"q": "Delhi"})
    assert r.status_code == 200
    assert r.json()["results"][0]["label"] == "Delhi, Delhi, India"

    assert client.get("/api/geocode", params={"q": "D"}).status_code == 422
    assert client.get("/api/geocode", params={"q": "Delhi", "lang": "fr"}).status_code == 422


def test_health_reports_ai_status_without_secrets(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert set(body["ai"]) == {"provider", "model", "configured", "problem"}
