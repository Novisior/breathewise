"""Shared fake Open-Meteo payloads for tests."""
from datetime import datetime, timedelta

START = datetime(2026, 9, 30, 14, 0)  # 24h "in the past" relative to NOW_IDX


def make_air_json(pm25=100.0, pm10=150.0, no2=40.0, o3=50.0, so2=20.0, co_ug=1000.0, hours=73):
    times = [(START + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)]
    return {
        "timezone": "Asia/Kolkata",
        "current": {"time": times[24], "pm2_5": pm25, "pm10": pm10,
                    "nitrogen_dioxide": no2, "ozone": o3,
                    "sulphur_dioxide": so2, "carbon_monoxide": co_ug},
        "hourly": {
            "time": times,
            "pm2_5": [pm25] * hours, "pm10": [pm10] * hours,
            "nitrogen_dioxide": [no2] * hours, "ozone": [o3] * hours,
            "sulphur_dioxide": [so2] * hours, "carbon_monoxide": [co_ug] * hours,
        },
    }


WEATHER_JSON = {"current": {"temperature_2m": 31.4, "relative_humidity_2m": 48}}
