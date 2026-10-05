"""Unit tests for the CPCB AQI module. Expected values are worked out by hand
from  I = (Ihi-Ilo)/(BPhi-BPlo) * (C-BPlo) + Ilo."""
import pytest

from app.aqi import (
    InsufficientDataError, aqi_at, calculate_aqi, category_for, sub_index, trailing_mean,
)


# (pollutant, concentration, expected sub-index)
KNOWN_CASES = [
    # --- PM2.5 band edges ---
    ("pm2_5", 0, 0),
    ("pm2_5", 30, 50),      # top of Good
    ("pm2_5", 31, 51),      # bottom of Satisfactory
    ("pm2_5", 60, 100),
    ("pm2_5", 61, 101),
    ("pm2_5", 90, 200),
    ("pm2_5", 91, 201),
    ("pm2_5", 120, 300),
    ("pm2_5", 250, 400),
    ("pm2_5", 380, 500),    # top of the table
    ("pm2_5", 900, 500),    # above the table is capped at 500
    # --- PM2.5 mid-band interpolation: 49/29*14+51 = 74.66 -> 75 ---
    ("pm2_5", 45, 75),
    # --- other pollutants ---
    ("pm10", 100, 100),
    ("pm10", 175, 150),     # 99/149*74+101 = 150.17
    ("no2", 60, 75),        # 49/39*19+51  = 74.87
    ("o3", 120, 129),       # 99/67*19+101 = 129.07
    ("so2", 40, 50),
    ("so2", 100, 107),      # 99/299*19+101 = 107.29
    ("co", 1.0, 50),        # CO is in mg/m3
    ("co", 1.1, 51),
    ("co", 5, 137),         # 99/7.9*2.9+101 = 137.34
]


@pytest.mark.parametrize("pollutant,conc,expected", KNOWN_CASES)
def test_sub_index_known_values(pollutant, conc, expected):
    assert sub_index(pollutant, conc) == expected


def test_value_inside_table_gap_is_clamped_up():
    # 30.5 sits between the 0-30 and 31-60 bands; it must not score below 51.
    assert sub_index("pm2_5", 30.5) == 51


def test_invalid_inputs_return_none():
    assert sub_index("pm2_5", None) is None
    assert sub_index("pm2_5", -5) is None
    assert sub_index("pm2_5", float("nan")) is None


def test_unknown_pollutant_raises():
    with pytest.raises(ValueError):
        sub_index("radon", 10)


def test_aqi_is_max_subindex_and_reports_dominant():
    # pm2_5=150 -> 323, pm10=200 -> 167, no2=50 -> 62
    r = calculate_aqi({"pm2_5": 150, "pm10": 200, "no2": 50})
    assert r.sub_indices == {"pm2_5": 323, "pm10": 167, "no2": 62}
    assert r.aqi == 323
    assert r.dominant == "pm2_5"
    assert r.category == "very_poor"


def test_dominant_can_be_a_gas():
    r = calculate_aqi({"pm2_5": 10, "pm10": 20, "o3": 300})  # o3 300 -> 301+ band
    assert r.dominant == "o3"
    assert r.aqi > r.sub_indices["pm2_5"]


@pytest.mark.parametrize("aqi,category", [
    (0, "good"), (50, "good"), (51, "satisfactory"), (100, "satisfactory"),
    (101, "moderate"), (200, "moderate"), (201, "poor"), (300, "poor"),
    (301, "very_poor"), (400, "very_poor"), (401, "severe"), (500, "severe"),
])
def test_category_boundaries(aqi, category):
    assert category_for(aqi) == category


def test_too_few_pollutants_raises():
    with pytest.raises(InsufficientDataError):
        calculate_aqi({"pm2_5": 50, "pm10": 80})  # only 2 pollutants


def test_needs_a_particulate_pollutant():
    with pytest.raises(InsufficientDataError):
        calculate_aqi({"no2": 50, "o3": 50, "so2": 50})  # 3 gases, no PM


# ---------------- trailing averages ----------------

def test_trailing_mean_full_window():
    assert trailing_mean([100.0] * 24, end=23, window=24, min_valid=16) == 100.0


def test_trailing_mean_requires_enough_valid_hours():
    data = [100.0] * 10 + [None] * 14
    assert trailing_mean(data, end=23, window=24, min_valid=16) is None
    data = [100.0] * 16 + [None] * 8
    assert trailing_mean(data, end=23, window=24, min_valid=16) == 100.0


def test_aqi_at_uses_24h_average_not_latest_hour():
    # 23 clean hours then one spike. The 24h mean is (23*20 + 380)/24 = 35,
    # so the spike must NOT dominate the AQI.
    pm25 = [20.0] * 23 + [380.0]
    series = {"pm2_5": pm25, "pm10": [40.0] * 24, "no2": [20.0] * 24}
    r = aqi_at(series, 23)
    assert r.inputs["pm2_5"] == 35.0
    assert r.sub_indices["pm2_5"] == 58  # 49/29*4+51 = 57.76
    assert r.approximate is False


def test_aqi_at_falls_back_to_instant_value_when_history_missing():
    # Only 3 hours of data -> not enough for a 24h average -> approximate.
    series = {"pm2_5": [90.0] * 3, "pm10": [100.0] * 3, "no2": [40.0] * 3}
    r = aqi_at(series, 2)
    assert r.approximate is True
    assert r.sub_indices["pm2_5"] == 200  # raw 90 -> top of Moderate


def test_instant_mode_uses_latest_hour_without_averaging():
    series = {"pm2_5": [20.0] * 23 + [380.0], "pm10": [40.0] * 24, "no2": [20.0] * 24}
    assert aqi_at(series, 23).inputs["pm2_5"] == 35.0                  # averaged
    inst = aqi_at(series, 23, instant=True)
    assert inst.inputs["pm2_5"] == 380.0                               # raw
    assert inst.aqi == 500 and inst.category == "severe"
