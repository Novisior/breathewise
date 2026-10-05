"""
Deterministic advice rules + the safety layer. Pure Python (no pydantic/network).

This module does four jobs:
  1. Decide the profile's risk level (stricter thresholds for sensitive people).
  2. Produce full rule-based advice in English or Hindi (the fallback that
     keeps the app working with no API key or when the AI fails).
  3. Compute the best/worst time windows from the forecast.
  4. Check and correct anything the AI returns (enforce_safety).

NOTE: the Hindi text was written by an AI assistant; have a native speaker
review it before any public demo.
"""
from __future__ import annotations

import re
import unicodedata

from app.aqi import CATEGORY_LABELS, category_for

CATEGORY_ORDER = tuple(CATEGORY_LABELS)  # good, satisfactory, moderate, poor, very_poor, severe
RISK_LEVELS = ("Low", "Moderate", "High", "Very High")
MASK_LEVELS = ("none", "surgical", "n95")

SENSITIVE_CONDITIONS = {"asthma", "copd", "heart_disease", "pregnancy"}
SENSITIVE_AGE_GROUPS = {"child", "senior"}
OUTDOOR_ROUTINES = {"outdoor_exercise", "outdoor_work", "commute_two_wheeler", "commute_walk"}
LIMIT_EXPOSURE_CATEGORIES = {"very_poor", "severe"}

FORECAST_HOURS_USED = 12
MAX_LIST_ITEMS = 5
FLAT_FORECAST_THRESHOLD = 15  # AQI points: smaller differences = "no clearly better time"

# Risk index (0=Low .. 3=Very High) per AQI category.
BASE_RISK_NORMAL = {"good": 0, "satisfactory": 0, "moderate": 0, "poor": 1, "very_poor": 2, "severe": 3}
# Stricter table for sensitive people: Moderate = cautionary, Poor or worse = High.
BASE_RISK_SENSITIVE = {"good": 0, "satisfactory": 0, "moderate": 1, "poor": 2, "very_poor": 3, "severe": 3}

DISCLAIMER = {
    "en": ("This is general guidance, not medical advice. If you feel unwell or have symptoms "
           "such as breathlessness, chest pain or a persistent cough, please consult a doctor."),
    "hi": ("यह सामान्य जानकारी है, चिकित्सकीय सलाह नहीं। अगर सांस फूलना, सीने में दर्द या "
           "लगातार खांसी जैसी तकलीफ हो, तो कृपया डॉक्टर से मिलें।"),
}

TEXT = {
    "en": {
        "labels": {"good": "Good", "satisfactory": "Satisfactory", "moderate": "Moderate",
                   "poor": "Poor", "very_poor": "Very Poor", "severe": "Severe"},
        "aqi_prefix": "AQI is {aqi} ({label}).",
        "summary_normal": [
            "Air is fine for your normal routine today.",
            "Air is unhealthy for long outdoor time, so plan lighter activity.",
            "Air is unhealthy today, so cut down your time outdoors.",
            "Air is very unhealthy today, so stay indoors as much as you can.",
        ],
        "summary_sensitive": [
            "Air is fine for your normal routine today.",
            "Air needs some care for you today, so keep outdoor time short.",
            "Air is unhealthy for you today, so avoid going outside where you can.",
            "Air is very unhealthy for you today, so stay indoors as much as you can.",
        ],
        "do": [
            ["Go about your normal routine.", "Open windows for fresh air when the air outside is clear."],
            ["Keep outdoor activity light and take breaks.", "Check the air quality again before evening plans."],
            ["Limit time outdoors, especially near busy roads.",
             "Keep windows closed and use an air purifier if you have one."],
            ["Limit outdoor exposure and stay indoors as much as possible.",
             "Keep windows closed and use an air purifier if you have one."],
        ],
        "avoid": [
            ["Nothing special to avoid today."],
            ["Long, hard exercise outside.", "Busy roads at peak traffic hours."],
            ["Outdoor exercise and heavy outdoor work.", "Burning waste, wood or incense, and smoky places."],
            ["Any outdoor exercise or long walks.", "Busy roads and smoky places."],
        ],
        "exercise": [
            "Outdoor exercise is fine today.",
            "Keep outdoor exercise light and short, or exercise indoors.",
            "Skip outdoor exercise today and exercise indoors instead.",
            "Do not exercise outdoors today; gentle indoor movement only.",
        ],
        "extra_doctor": "Follow your doctor's usual advice for days with poor air.",
        "extra_child": "Keep children's play indoors today.",
        "extra_senior": "Ask family or neighbours to help with errands outside.",
        "extra_work": "If you must work outside, take frequent breaks in cleaner indoor air.",
        "extra_commute": "On the road, wear a well-fitted N95 mask and avoid busy routes.",
        "limit_exposure": "Limit outdoor exposure and stay indoors as much as possible.",
        "window_best": "Best time: {best} (lowest expected AQI in the next 12 hours). Avoid {worst}.",
        "window_flat": "Air quality stays about the same for the next 12 hours, so no time is clearly better.",
        "window_none": "Not enough forecast data yet; please check again later.",
    },
    "hi": {
        "labels": {"good": "अच्छा", "satisfactory": "संतोषजनक", "moderate": "मध्यम",
                   "poor": "खराब", "very_poor": "बहुत खराब", "severe": "गंभीर"},
        "aqi_prefix": "AQI {aqi} ({label}) है।",
        "summary_normal": [
            "आज की हवा आपकी रोज़ की दिनचर्या के लिए ठीक है।",
            "लंबे समय तक बाहर रहने के लिए हवा ठीक नहीं है, इसलिए हल्की गतिविधि रखें।",
            "आज हवा हानिकारक है, इसलिए बाहर कम समय बिताएं।",
            "आज हवा बहुत हानिकारक है, इसलिए जितना हो सके घर के अंदर रहें।",
        ],
        "summary_sensitive": [
            "आज की हवा आपकी रोज़ की दिनचर्या के लिए ठीक है।",
            "आज आपको हवा से थोड़ी सावधानी रखनी चाहिए, इसलिए बाहर कम समय बिताएं।",
            "आज हवा आपके लिए हानिकारक है, इसलिए जहां तक हो सके बाहर न जाएं।",
            "आज हवा आपके लिए बहुत हानिकारक है, इसलिए जितना हो सके घर के अंदर रहें।",
        ],
        "do": [
            ["अपनी सामान्य दिनचर्या जारी रखें।", "बाहर की हवा साफ़ हो तो खिड़कियां खोलें।"],
            ["बाहर की गतिविधि हल्की रखें और बीच-बीच में आराम करें।",
             "शाम की योजना से पहले हवा की गुणवत्ता दोबारा देखें।"],
            ["बाहर कम समय बिताएं, खासकर भीड़भाड़ वाली सड़कों के पास।",
             "खिड़कियां बंद रखें और एयर प्यूरीफायर हो तो चलाएं।"],
            ["बाहर निकलना सीमित करें और जितना हो सके घर के अंदर रहें।",
             "खिड़कियां बंद रखें और एयर प्यूरीफायर हो तो चलाएं।"],
        ],
        "avoid": [
            ["आज बचने के लिए कुछ खास नहीं है।"],
            ["बाहर लंबी और कठिन कसरत।", "भीड़ के समय व्यस्त सड़कें।"],
            ["बाहर कसरत और भारी मेहनत वाला काम।", "कचरा, लकड़ी या धूप जलाना और धुएं वाली जगहें।"],
            ["बाहर कोई भी कसरत या लंबी सैर।", "व्यस्त सड़कें और धुएं वाली जगहें।"],
        ],
        "exercise": [
            "आज बाहर कसरत करना ठीक है।",
            "बाहर की कसरत हल्की और कम समय की रखें, या घर के अंदर करें।",
            "आज बाहर कसरत न करें, घर के अंदर करें।",
            "आज बाहर बिल्कुल कसरत न करें; घर के अंदर सिर्फ हल्की गतिविधि करें।",
        ],
        "extra_doctor": "खराब हवा वाले दिनों के लिए अपने डॉक्टर की सामान्य सलाह मानें।",
        "extra_child": "आज बच्चों का खेल घर के अंदर रखें।",
        "extra_senior": "बाहर के कामों के लिए परिवार या पड़ोसियों से मदद लें।",
        "extra_work": "बाहर काम करना ही पड़े तो बीच-बीच में साफ़ हवा वाली जगह में आराम करें।",
        "extra_commute": "सड़क पर अच्छी फिटिंग वाला N95 मास्क पहनें और भीड़ वाले रास्तों से बचें।",
        "limit_exposure": "बाहर निकलना सीमित करें और जितना हो सके घर के अंदर रहें।",
        "window_best": "सबसे अच्छा समय: {best} (अगले 12 घंटों में सबसे कम AQI)। {worst} से बचें।",
        "window_flat": "अगले 12 घंटों में हवा की गुणवत्ता लगभग एक जैसी रहेगी, इसलिए कोई समय खास बेहतर नहीं है।",
        "window_none": "पूर्वानुमान का डेटा अभी कम है; कृपया बाद में फिर देखें।",
    },
}


# ----------------------------------------------------------------------
# Context + risk
# ----------------------------------------------------------------------

def build_context(profile: dict, language: str, air: dict) -> dict:
    """
    Normalise request data into one plain dict used by everything below.
    The AQI category is RECOMPUTED from the number; any category sent by the
    client is ignored, so a tampered request cannot understate the danger.
    """
    aqi = int(air["aqi"])
    inst = air.get("aqi_instant")
    forecast = []
    for pt in (air.get("forecast") or [])[:FORECAST_HOURS_USED]:
        pt_inst = pt.get("aqi_instant")
        forecast.append({
            "time": pt["time"],
            "aqi": int(pt["aqi"]),
            "category": category_for(int(pt["aqi"])),
            "aqi_instant": None if pt_inst is None else int(pt_inst),
            "category_instant": None if pt_inst is None else category_for(int(pt_inst)),
            "dominant": pt.get("dominant"),
            "pm2_5": pt.get("pm2_5"),
        })
    return {
        "language": language if language in TEXT else "en",
        "profile": {
            "age_group": profile.get("age_group", "adult"),
            "conditions": sorted({c for c in profile.get("conditions", []) if c != "none"}),
            "routine": sorted(set(profile.get("routine", []))),
        },
        "air": {
            "aqi": aqi,
            "category": category_for(aqi),
            "aqi_instant": None if inst is None else int(inst),
            "category_instant": None if inst is None else category_for(int(inst)),
            "dominant": air.get("dominant"),
            "pollutants": dict(air.get("pollutants") or {}),
            "forecast": forecast,
        },
    }


def is_sensitive(profile: dict) -> bool:
    return (bool(SENSITIVE_CONDITIONS & set(profile.get("conditions", [])))
            or profile.get("age_group") in SENSITIVE_AGE_GROUPS)


def worse_category(a: str | None, b: str | None) -> str | None:
    if a is None or b is None:
        return a or b
    return a if CATEGORY_ORDER.index(a) >= CATEGORY_ORDER.index(b) else b


def effective_category(ctx: dict) -> str:
    """Sensitive people are judged on the worse of the official and 'right now' AQI."""
    air = ctx["air"]
    if is_sensitive(ctx["profile"]):
        return worse_category(air["category"], air["category_instant"])
    return air["category"]


def risk_index(ctx: dict) -> int:
    profile = ctx["profile"]
    cat = effective_category(ctx)
    table = BASE_RISK_SENSITIVE if is_sensitive(profile) else BASE_RISK_NORMAL
    idx = table[cat]
    # Spending time outdoors raises exposure: bump one level when air is Poor or worse.
    if (CATEGORY_ORDER.index(cat) >= CATEGORY_ORDER.index("poor")
            and idx in (1, 2) and OUTDOOR_ROUTINES & set(profile["routine"])):
        idx += 1
    return idx


def risk_level(ctx: dict) -> str:
    return RISK_LEVELS[risk_index(ctx)]


def mask_for_index(idx: int) -> str:
    return MASK_LEVELS[0 if idx == 0 else 1 if idx == 1 else 2]


def stricter_mask(a: str, b: str) -> str:
    return a if MASK_LEVELS.index(a) >= MASK_LEVELS.index(b) else b


def fingerprint(profile: dict) -> str:
    return "|".join([profile["age_group"], ",".join(profile["conditions"]), ",".join(profile["routine"])])


def cache_key(ctx: dict) -> tuple:
    """(language, AQI category, profile). 'Right now' category only matters for sensitive profiles."""
    air = ctx["air"]
    inst = air["category_instant"] if is_sensitive(ctx["profile"]) else None
    return (ctx["language"], air["category"], inst, fingerprint(ctx["profile"]))


# ----------------------------------------------------------------------
# Best / worst time windows (computed from data, never invented)
# ----------------------------------------------------------------------

def compute_window_text(ctx: dict) -> str | None:
    """Localised best/worst window text, or None if the forecast is too short."""
    pts = ctx["air"]["forecast"][:FORECAST_HOURS_USED]
    if len(pts) < 3:
        return None
    t = TEXT[ctx["language"]]
    vals = [p["aqi_instant"] if p["aqi_instant"] is not None else p["aqi"] for p in pts]
    hours = [int(p["time"][11:13]) for p in pts]
    windows = [((vals[i] + vals[i + 1]) / 2, i) for i in range(len(vals) - 1)]  # 2-hour windows
    best, worst = min(windows), max(windows)
    if worst[0] - best[0] < FLAT_FORECAST_THRESHOLD:
        return t["window_flat"]

    def fmt(i: int) -> str:
        return f"{hours[i]:02d}:00–{(hours[i] + 2) % 24:02d}:00"

    return t["window_best"].format(best=fmt(best[1]), worst=fmt(worst[1]))


# ----------------------------------------------------------------------
# Rule-based advice (the fallback)
# ----------------------------------------------------------------------

def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", s)


_LIMIT_EN = re.compile(
    r"\b(limit|avoid|reduce|minimi[sz]e|stay|cut)\b.{0,50}\b(outdoors?|outside|indoors?|inside)\b", re.I)
_LIMIT_HI_VERBS = tuple(_norm(w) for w in ("सीमित", "कम", "न जाएं", "बचें", "रोक"))
_LIMIT_HI_PHRASES = tuple(_norm(w) for w in ("घर के अंदर", "घर में रहें"))


def mentions_limit_exposure(text: str, lang: str) -> bool:
    """Heuristic: does this line tell the user to limit outdoor exposure?"""
    if lang == "hi":
        s = _norm(text)
        return (_norm("बाहर") in s and any(v in s for v in _LIMIT_HI_VERBS)) or \
            any(p in s for p in _LIMIT_HI_PHRASES)
    return bool(_LIMIT_EN.search(text))


def needs_limit_exposure(ctx: dict) -> bool:
    air = ctx["air"]
    return bool(LIMIT_EXPOSURE_CATEGORIES & {air["category"], air["category_instant"]})


def ensure_limit_exposure(do_list: list[str], ctx: dict) -> list[str]:
    """If AQI is Very Poor/Severe, guarantee a 'limit outdoor exposure' item."""
    if not needs_limit_exposure(ctx):
        return do_list
    lang = ctx["language"]
    if any(mentions_limit_exposure(s, lang) for s in do_list):
        return do_list
    return [TEXT[lang]["limit_exposure"]] + do_list


def rules_core(ctx: dict) -> dict:
    """Complete advice from the rules table. Never fails, never calls the network."""
    lang = ctx["language"]
    t = TEXT[lang]
    profile, air = ctx["profile"], ctx["air"]
    idx = risk_index(ctx)
    sensitive = is_sensitive(profile)

    summary = (t["aqi_prefix"].format(aqi=air["aqi"], label=t["labels"][air["category"]]) + " "
               + (t["summary_sensitive"] if sensitive else t["summary_normal"])[idx])

    do = list(t["do"][idx])
    routine = set(profile["routine"])
    if sensitive and idx >= 1:
        do.append(t["extra_doctor"])
    if idx >= 2:
        if profile["age_group"] == "child":
            do.append(t["extra_child"])
        if profile["age_group"] == "senior":
            do.append(t["extra_senior"])
        if "outdoor_work" in routine:
            do.append(t["extra_work"])
        if {"commute_two_wheeler", "commute_walk"} & routine:
            do.append(t["extra_commute"])
    do = ensure_limit_exposure(do, ctx)[:MAX_LIST_ITEMS]

    return {
        "risk_level": RISK_LEVELS[idx],
        "summary": summary,
        "do": do,
        "avoid": list(t["avoid"][idx]),
        "mask": mask_for_index(idx),
        "exercise_advice": t["exercise"][idx],
        "best_time_window": compute_window_text(ctx) or t["window_none"],
    }


def with_fresh_window(core: dict, ctx: dict) -> dict:
    """Swap in a best-time window computed from the CURRENT forecast (used for cached advice)."""
    window = compute_window_text(ctx)
    return {**core, "best_time_window": window} if window else core


# ----------------------------------------------------------------------
# Safety layer for AI output
# ----------------------------------------------------------------------

_MED_EN = (r"(medic\w*|dose\w*|dosage|inhaler\w*|tablet\w*|pill\w*|puff\w*|drug\w*|"
           r"prescription\w*|steroid\w*)")
_CHANGE_EN = (r"(stop\w*|skip\w*|chang\w*|increas\w*|decreas\w*|reduc\w*|doubl\w*|adjust\w*|"
              r"discontinu\w*|halv\w*|switch\w*|avoid\w*|quit\w*|extra|additional|more)")
_MED_CHANGE_EN = re.compile(
    rf"\b{_CHANGE_EN}\b[^.!?]{{0,40}}\b{_MED_EN}|\b{_MED_EN}\b[^.!?]{{0,40}}\b{_CHANGE_EN}\b", re.I)
_DIAGNOSE_EN = re.compile(r"diagnos", re.I)

# No \b for Hindi: Python's word boundaries misbehave around Devanagari vowel signs.
_MED_HI = "(" + "|".join(_norm(w) for w in
                         ("दवा", "दवाई", "दवाइयां", "दवाइयाँ", "इन्हेलर", "खुराक", "गोली", "गोलियां")) + ")"
_CHANGE_HI = "(" + "|".join(_norm(w) for w in
                            ("बंद", "छोड़", "बदल", "बढ़ा", "घटा", "कम कर", "ज़्यादा", "ज्यादा", "दोगुन", "रोक")) + ")"
_MED_CHANGE_HI = re.compile(
    rf"{_MED_HI}[^।.!?]{{0,40}}{_CHANGE_HI}|{_CHANGE_HI}[^।.!?]{{0,40}}{_MED_HI}")
_DIAGNOSE_HI = re.compile(_norm("निदान"))


def _all_text(core: dict) -> list[str]:
    return ([core.get("summary", ""), core.get("exercise_advice", ""), core.get("best_time_window", "")]
            + list(core.get("do", [])) + list(core.get("avoid", [])))


def contains_forbidden_text(core: dict) -> bool:
    """True if any field diagnoses, or suggests changing/stopping medication."""
    for text in _all_text(core):
        if _MED_CHANGE_EN.search(text) or _DIAGNOSE_EN.search(text):
            return True
        n = _norm(text)
        if _MED_CHANGE_HI.search(n) or _DIAGNOSE_HI.search(n):
            return True
    return False


def enforce_safety(core: dict, ctx: dict, rules: dict) -> dict | None:
    """
    Check AI advice against the rules. Returns corrected advice, or None if the
    AI answer must be discarded (caller then uses the rules advice).

      * forbidden medical text          -> discard
      * risk lower than the rules floor -> discard (AI may be MORE cautious, never less)
      * mask weaker than the rules      -> raised to the rules' mask
      * Very Poor/Severe without a 'limit outdoor exposure' line -> added by code
      * best-time window                -> replaced by one computed from the forecast
    """
    if contains_forbidden_text(core):
        return None
    if RISK_LEVELS.index(core["risk_level"]) < RISK_LEVELS.index(rules["risk_level"]):
        return None

    out = dict(core)
    out["do"] = [s.strip() for s in core["do"] if s and s.strip()] or list(rules["do"])
    out["avoid"] = [s.strip() for s in core["avoid"] if s and s.strip()]
    out["mask"] = stricter_mask(core["mask"], rules["mask"])
    out["do"] = ensure_limit_exposure(out["do"], ctx)[:MAX_LIST_ITEMS]
    out["avoid"] = out["avoid"][:MAX_LIST_ITEMS]
    window = compute_window_text(ctx)
    if window:
        out["best_time_window"] = window
    return out
