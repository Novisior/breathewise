"""
aqi.py - Indian AQI (CPCB National AQI) calculator.

Pure Python: no third-party imports, so it is easy to test and reason about.

HOW THE INDIAN AQI WORKS
  1. For each pollutant, convert its (averaged) concentration into a
     "sub-index" (0-500) by linear interpolation inside a breakpoint band.
  2. The overall AQI is the MAXIMUM sub-index. The pollutant that produces
     it is the "dominant pollutant".
  3. Averaging periods used by CPCB: PM2.5, PM10, NO2, SO2 -> 24 hours;
     O3 and CO -> 8 hours. Open-Meteo gives hourly values, so we compute
     trailing averages (see `aqi_at`).
  4. CPCB needs at least 3 pollutants, one of them PM2.5 or PM10.

UNITS: ug/m3 for everything EXCEPT CO, which is mg/m3.

!!! BREAKPOINT TABLE SOURCE / PLEASE VERIFY !!!
  The table below follows the CPCB "National Air Quality Index" (2014)
  breakpoint scheme, written from memory of that publication. Please
  double-check every number against CPCB's official documentation
  (https://cpcb.nic.in -> National Air Quality Index) before relying on it.
  The top band ("Severe", 401-500) has no official upper concentration;
  the caps used here (e.g. PM2.5 380) are common conventions, and any
  value above the cap simply returns 500.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping, Sequence

# Order matters: on a tie, the earlier pollutant is reported as dominant.
POLLUTANTS = ("pm2_5", "pm10", "no2", "o3", "co", "so2")

# The six AQI index bands, shared by every pollutant.
INDEX_BANDS = ((0, 50), (51, 100), (101, 200), (201, 300), (301, 400), (401, 500))

# Concentration (low, high) for each index band, per pollutant.
BREAKPOINTS: dict[str, tuple[tuple[float, float], ...]] = {
    "pm2_5": ((0, 30), (31, 60), (61, 90), (91, 120), (121, 250), (250, 380)),
    "pm10": ((0, 50), (51, 100), (101, 250), (251, 350), (351, 430), (430, 510)),
    "no2": ((0, 40), (41, 80), (81, 180), (181, 280), (281, 400), (400, 510)),
    "o3": ((0, 50), (51, 100), (101, 168), (169, 208), (209, 748), (748, 1000)),
    "co": ((0, 1.0), (1.1, 2.0), (2.1, 10), (10.1, 17), (17.1, 34), (34, 50)),
    "so2": ((0, 40), (41, 80), (81, 380), (381, 800), (801, 1600), (1600, 2000)),
}

# (window_hours, minimum_valid_hours) used for trailing averages.
AVERAGING: dict[str, tuple[int, int]] = {
    "pm2_5": (24, 16),
    "pm10": (24, 16),
    "no2": (24, 16),
    "so2": (24, 16),
    "o3": (8, 6),
    "co": (8, 6),
}

CATEGORY_LABELS = {
    "good": "Good",
    "satisfactory": "Satisfactory",
    "moderate": "Moderate",
    "poor": "Poor",
    "very_poor": "Very Poor",
    "severe": "Severe",
}


class InsufficientDataError(ValueError):
    """Raised when there is not enough pollutant data to compute a valid AQI."""


@dataclass
class AqiResult:
    aqi: int
    category: str                      # key from CATEGORY_LABELS
    dominant: str                      # pollutant key, e.g. "pm2_5"
    sub_indices: dict[str, int] = field(default_factory=dict)
    inputs: dict[str, float | None] = field(default_factory=dict)  # averaged values used
    approximate: bool = False          # True if some pollutant lacked enough history


def _round_half_up(x: float) -> int:
    # Python's round() rounds .5 to even; AQI reporting conventionally rounds half up.
    return int(math.floor(x + 0.5))


def category_for(aqi: int) -> str:
    """Map an AQI number to its CPCB category key."""
    if aqi <= 50:
        return "good"
    if aqi <= 100:
        return "satisfactory"
    if aqi <= 200:
        return "moderate"
    if aqi <= 300:
        return "poor"
    if aqi <= 400:
        return "very_poor"
    return "severe"


def sub_index(pollutant: str, concentration: float | None) -> int | None:
    """
    Sub-index for one pollutant, or None if the value is missing/invalid.

    Formula (per CPCB):  I = (Ihi - Ilo) / (BPhi - BPlo) * (C - BPlo) + Ilo
    """
    if pollutant not in BREAKPOINTS:
        raise ValueError(f"Unknown pollutant: {pollutant!r}")
    if concentration is None or not math.isfinite(concentration) or concentration < 0:
        return None

    for (bp_lo, bp_hi), (i_lo, i_hi) in zip(BREAKPOINTS[pollutant], INDEX_BANDS):
        if concentration <= bp_hi:
            fraction = (concentration - bp_lo) / (bp_hi - bp_lo)
            # Tables have small gaps (e.g. PM2.5 30 -> 31). A value inside a gap
            # lands in the next band with a negative fraction; clamp it to the
            # band's lowest index.
            fraction = max(0.0, fraction)
            return _round_half_up(i_lo + fraction * (i_hi - i_lo))
    return 500  # above the top of the table


def calculate_aqi(concentrations: Mapping[str, float | None]) -> AqiResult:
    """
    Overall AQI from already-averaged concentrations.
    Keys: pm2_5, pm10, no2, o3, co (mg/m3!), so2.
    """
    subs: dict[str, int] = {}
    for p in POLLUTANTS:
        si = sub_index(p, concentrations.get(p))
        if si is not None:
            subs[p] = si

    if len(subs) < 3 or not ("pm2_5" in subs or "pm10" in subs):
        raise InsufficientDataError(
            "Need at least 3 pollutants including PM2.5 or PM10 to compute AQI."
        )

    dominant = max(subs, key=lambda p: subs[p])  # first max wins -> POLLUTANTS order
    aqi = subs[dominant]
    return AqiResult(
        aqi=aqi,
        category=category_for(aqi),
        dominant=dominant,
        sub_indices=subs,
        inputs={p: concentrations.get(p) for p in POLLUTANTS},
    )


def _is_valid(x: float | None) -> bool:
    return x is not None and math.isfinite(x)


def trailing_mean(
    values: Sequence[float | None], end: int, window: int, min_valid: int
) -> float | None:
    """Mean of values[end-window+1 .. end]; None if fewer than min_valid are valid."""
    chunk = values[max(0, end - window + 1): end + 1]
    valid = [v for v in chunk if _is_valid(v)]
    if len(valid) < min_valid:
        return None
    return sum(valid) / len(valid)


def aqi_at(series: Mapping[str, Sequence[float | None]], index: int,
           instant: bool = False) -> AqiResult:
    """
    AQI for the hour at `index`, using CPCB-style trailing averages
    (24h for PM/NO2/SO2, 8h for O3/CO). `series` maps pollutant -> hourly list
    (CO must already be in mg/m3).

    If a pollutant lacks enough history, we fall back to its instantaneous
    value and mark the result `approximate=True`.

    instant=True skips averaging and uses each hour's raw values. This is NOT
    the official CPCB method; it shows how air quality changes hour to hour
    (used for the forecast chart and best-time planner, which the smoothed
    24h-average AQI would flatten).
    """
    averaged: dict[str, float | None] = {}
    approximate = False
    for p in POLLUTANTS:
        values = series.get(p)
        if not values:
            averaged[p] = None
            continue
        if instant:
            raw = values[index] if 0 <= index < len(values) else None
            averaged[p] = raw if _is_valid(raw) else None
            continue
        window, min_valid = AVERAGING[p]
        mean = trailing_mean(values, index, window, min_valid)
        if mean is None:
            raw = values[index] if 0 <= index < len(values) else None
            if _is_valid(raw):
                mean = raw
                approximate = True
        averaged[p] = mean

    result = calculate_aqi(averaged)
    result.approximate = approximate
    return result
