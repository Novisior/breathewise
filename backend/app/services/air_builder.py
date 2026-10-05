"""
Turns raw Open-Meteo JSON into our API response (plain dicts).

Kept free of httpx/pydantic so it can be unit-tested without a network.
"""
from __future__ import annotations

from app.aqi import CATEGORY_LABELS, InsufficientDataError, aqi_at

# Our pollutant key -> Open-Meteo hourly/current variable name.
OPEN_METEO_NAMES = {
    "pm2_5": "pm2_5",
    "pm10": "pm10",
    "no2": "nitrogen_dioxide",
    "o3": "ozone",
    "so2": "sulphur_dioxide",
    "co": "carbon_monoxide",
}
AIR_VARIABLES = ",".join(OPEN_METEO_NAMES.values())

PAST_HOURS = 24      # history requested so the 24h averages are real
FORECAST_HOURS = 48  # how far ahead we forecast


def _co_to_mg(ug_per_m3: float | None) -> float | None:
    """Open-Meteo reports CO in ug/m3; CPCB uses mg/m3."""
    return None if ug_per_m3 is None else ug_per_m3 / 1000.0


def _r(x: float | None, digits: int = 1) -> float | None:
    return None if x is None else round(x, digits)


def _current_index(times: list[str], current_time: str | None) -> int:
    """Index of the latest hourly slot that is <= the `current` timestamp."""
    if not times:
        raise InsufficientDataError("No hourly data returned.")
    if current_time:
        best = 0
        for i, t in enumerate(times):
            if t <= current_time:  # ISO strings in the same format sort correctly
                best = i
        return best
    return min(PAST_HOURS, len(times) - 1)


def _instant(series: dict, i: int) -> tuple[int | None, str | None]:
    """Hour-by-hour (unaveraged) AQI, or (None, None) if data is unusable."""
    try:
        r = aqi_at(series, i, instant=True)
        return r.aqi, r.category
    except InsufficientDataError:
        return None, None


def build_air_payload(air_json: dict, weather_json: dict | None, lat: float,
                      lon: float, updated_at: str) -> dict:
    hourly = air_json.get("hourly") or {}
    times: list[str] = hourly.get("time") or []
    n = len(times)

    series: dict[str, list[float | None]] = {}
    for key, om_name in OPEN_METEO_NAMES.items():
        values = list(hourly.get(om_name) or [None] * n)
        series[key] = [_co_to_mg(v) for v in values] if key == "co" else values

    current = air_json.get("current") or {}
    idx = _current_index(times, current.get("time"))

    now = aqi_at(series, idx)  # raises InsufficientDataError if data is unusable
    now_instant, now_instant_cat = _instant(series, idx)

    # Display values: the latest instantaneous reading (not the averaged ones).
    pollutants = {}
    for key, om_name in OPEN_METEO_NAMES.items():
        raw = current.get(om_name)
        if raw is None:
            raw = hourly.get(om_name, [None] * n)[idx] if n else None
        pollutants[key] = _r(_co_to_mg(raw) if key == "co" else raw, 2 if key == "co" else 1)

    forecast = []
    for i in range(idx, min(idx + FORECAST_HOURS, n)):
        try:
            r = aqi_at(series, i)
        except InsufficientDataError:
            continue  # skip hours with unusable data rather than failing everything
        inst, inst_cat = _instant(series, i)
        forecast.append({
            "time": times[i],
            "aqi": r.aqi,
            "category": r.category,
            "aqi_instant": inst,
            "category_instant": inst_cat,
            "dominant": r.dominant,
            "pm2_5": _r(series["pm2_5"][i]),
        })

    w_current = (weather_json or {}).get("current") or {}
    return {
        "location": {
            "latitude": lat,
            "longitude": lon,
            "timezone": air_json.get("timezone"),
        },
        "observed_at": times[idx],
        "updated_at": updated_at,
        "aqi": now.aqi,
        "category": now.category,
        "category_label": CATEGORY_LABELS[now.category],
        "dominant": now.dominant,
        "aqi_instant": now_instant,
        "category_instant": now_instant_cat,
        "approximate": now.approximate,
        "pollutants": pollutants,
        "sub_indices": now.sub_indices,
        "weather": {
            "temperature_c": _r(w_current.get("temperature_2m")),
            "humidity_pct": _r(w_current.get("relative_humidity_2m"), 0),
        },
        "forecast": forecast,
    }


def normalize_geocode(geo_json: dict) -> list[dict]:
    """Open-Meteo omits 'results' entirely when nothing matches."""
    out = []
    for r in geo_json.get("results") or []:
        if "latitude" not in r or "longitude" not in r or not r.get("name"):
            continue
        parts = [r["name"], r.get("admin1"), r.get("country")]
        out.append({
            "name": r["name"],
            "admin1": r.get("admin1"),
            "country": r.get("country"),
            "country_code": r.get("country_code"),
            "latitude": r["latitude"],
            "longitude": r["longitude"],
            "label": ", ".join(p for p in parts if p),
        })
    return out
