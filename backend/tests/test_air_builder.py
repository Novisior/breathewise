"""Tests for turning raw Open-Meteo JSON into our API payload."""
from app.services.air_builder import build_air_payload, normalize_geocode
from tests.helpers import WEATHER_JSON, make_air_json

UPDATED = "2026-10-01T09:00:00+00:00"


def test_payload_aqi_category_and_dominant():
    p = build_air_payload(make_air_json(), WEATHER_JSON, 28.61, 77.21, UPDATED)
    # Constant PM2.5=100: 99/29*9+201 = 231.7 -> 232 (Poor), PM2.5 dominates.
    assert p["aqi"] == 232
    assert p["category"] == "poor"
    assert p["category_label"] == "Poor"
    assert p["dominant"] == "pm2_5"
    assert p["approximate"] is False


def test_co_is_converted_from_ug_to_mg():
    p = build_air_payload(make_air_json(co_ug=2000.0), None, 28.61, 77.21, UPDATED)
    assert p["pollutants"]["co"] == 2.0


def test_forecast_starts_at_current_hour_and_has_48_points():
    air = make_air_json()
    p = build_air_payload(air, None, 28.61, 77.21, UPDATED)
    assert len(p["forecast"]) == 48
    assert p["forecast"][0]["time"] == air["current"]["time"]
    assert p["observed_at"] == air["current"]["time"]


def test_weather_is_optional():
    p = build_air_payload(make_air_json(), None, 28.61, 77.21, UPDATED)
    assert p["weather"] == {"temperature_c": None, "humidity_pct": None}
    p = build_air_payload(make_air_json(), WEATHER_JSON, 28.61, 77.21, UPDATED)
    assert p["weather"] == {"temperature_c": 31.4, "humidity_pct": 48}


def test_severe_air_is_reported_as_severe():
    p = build_air_payload(make_air_json(pm25=400.0, pm10=600.0), None, 28.6, 77.2, UPDATED)
    assert p["aqi"] == 500
    assert p["category"] == "severe"


def test_geocode_normalization_and_empty_results():
    raw = {"results": [
        {"name": "Delhi", "admin1": "Delhi", "country": "India", "country_code": "IN",
         "latitude": 28.65, "longitude": 77.23},
        {"name": "Broken"},  # missing coordinates -> skipped
    ]}
    out = normalize_geocode(raw)
    assert len(out) == 1
    assert out[0]["label"] == "Delhi, Delhi, India"
    assert normalize_geocode({"generationtime_ms": 0.3}) == []  # API omits "results"


def test_instant_aqi_shows_spikes_that_the_24h_average_smooths_out():
    air = make_air_json()                       # PM2.5 = 100 everywhere
    air["hourly"]["pm2_5"][24] = 300.0          # spike at the current hour
    air["current"]["pm2_5"] = 300.0
    p = build_air_payload(air, None, 28.6, 77.2, UPDATED)
    # 24h mean = (23*100+300)/24 = 108.3 -> 99/29*17.33+201 = 260 (Poor)
    assert p["aqi"] == 260 and p["category"] == "poor"
    # instant: 300 > 250 -> 50/130*99+401 = 439 (Severe)
    assert p["aqi_instant"] == 439 and p["category_instant"] == "severe"
    assert p["forecast"][0]["aqi_instant"] == 439
    assert p["forecast"][1]["aqi_instant"] == 232   # next hour is back to 100
