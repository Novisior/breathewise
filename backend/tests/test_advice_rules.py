"""Rules, risk thresholds and the safety layer (pure Python, no network)."""
import re

from app.services import advice_rules as r

DEVANAGARI = re.compile(r"[\u0900-\u097F]")


def pt(hour, aqi, inst=None, day="2026-10-01"):
    return {"time": f"{day}T{hour:02d}:00", "aqi": aqi, "aqi_instant": inst, "dominant": "pm2_5", "pm2_5": 50}


def make_ctx(aqi=219, inst=None, age="adult", conditions=(), routine=("mostly_indoors",),
             lang="en", forecast=None):
    air = {"aqi": aqi, "aqi_instant": inst, "dominant": "pm10", "pollutants": {}, "forecast": forecast or []}
    profile = {"age_group": age, "conditions": list(conditions), "routine": list(routine)}
    return r.build_context(profile, lang, air)


# ---------------- risk thresholds ----------------

def test_same_aqi_gives_different_risk_for_different_profiles():
    # AQI 219 = "poor". This is the demo case: healthy adult vs asthmatic child.
    assert r.risk_level(make_ctx(219)) == "Moderate"
    assert r.risk_level(make_ctx(219, age="child", conditions=["asthma"])) == "High"


def test_sensitive_thresholds_are_stricter_at_moderate():
    # "moderate" (AQI 150): healthy adult Low; every sensitive group at least Moderate.
    assert r.risk_level(make_ctx(150)) == "Low"
    for kwargs in (dict(age="senior"), dict(age="child"), dict(conditions=["asthma"]),
                   dict(conditions=["copd"]), dict(conditions=["heart_disease"]),
                   dict(conditions=["pregnancy"])):
        assert r.risk_level(make_ctx(150, **kwargs)) == "Moderate", kwargs


def test_sensitive_poor_or_worse_is_high_or_above():
    assert r.risk_level(make_ctx(250, conditions=["copd"])) == "High"
    assert r.risk_level(make_ctx(350, conditions=["copd"])) == "Very High"
    assert r.risk_level(make_ctx(450, conditions=["copd"])) == "Very High"


def test_diabetes_alone_is_not_sensitive():
    assert r.is_sensitive({"age_group": "adult", "conditions": ["diabetes"]}) is False


def test_everyone_gets_very_high_at_severe():
    assert r.risk_level(make_ctx(450)) == "Very High"


def test_sensitive_users_are_judged_on_worse_of_official_and_instant():
    # Official "moderate" but right-now "poor": sensitive -> High; healthy adult ignores instant -> Low.
    assert r.risk_level(make_ctx(150, inst=250, conditions=["asthma"])) == "High"
    assert r.risk_level(make_ctx(150, inst=250)) == "Low"


def test_outdoor_routine_raises_risk_when_air_is_poor():
    assert r.risk_level(make_ctx(219, routine=["outdoor_exercise"])) == "High"
    assert r.risk_level(make_ctx(150, routine=["outdoor_exercise"])) == "Low"  # no bump below Poor


def test_category_is_recomputed_from_aqi_not_trusted_from_client():
    air = {"aqi": 450, "category": "good", "aqi_instant": None, "dominant": "pm10", "forecast": []}
    ctx = r.build_context({"age_group": "adult"}, "en", air)
    assert ctx["air"]["category"] == "severe"


# ---------------- rule-based advice ----------------

def test_rules_advice_has_every_field_in_both_languages():
    for lang in ("en", "hi"):
        core = r.rules_core(make_ctx(219, age="child", conditions=["asthma"], lang=lang))
        assert core["risk_level"] == "High" and core["mask"] == "n95"
        assert core["summary"] and core["exercise_advice"] and core["best_time_window"]
        assert core["do"] and core["avoid"] and len(core["do"]) <= 5
    hi = r.rules_core(make_ctx(219, lang="hi"))
    assert DEVANAGARI.search(hi["summary"]) and DEVANAGARI.search(hi["do"][0])


def test_rules_output_differs_by_profile():
    adult = r.rules_core(make_ctx(219))
    child = r.rules_core(make_ctx(219, age="child", conditions=["asthma"]))
    assert adult["risk_level"] != child["risk_level"]
    assert adult["mask"] == "surgical" and child["mask"] == "n95"
    assert adult["exercise_advice"] != child["exercise_advice"]
    assert any("children" in s.lower() for s in child["do"])


def test_masks_by_risk():
    assert r.rules_core(make_ctx(40))["mask"] == "none"
    assert r.rules_core(make_ctx(150, age="senior"))["mask"] == "surgical"
    assert r.rules_core(make_ctx(450))["mask"] == "n95"


def test_very_poor_and_severe_always_limit_outdoor_exposure():
    for aqi in (350, 450):
        for lang in ("en", "hi"):
            for kwargs in ({}, {"age": "child"}, {"conditions": ["asthma"]}):
                core = r.rules_core(make_ctx(aqi, lang=lang, **kwargs))
                assert any(r.mentions_limit_exposure(s, lang) for s in core["do"]), (aqi, lang, kwargs)


def test_rules_advice_never_mentions_medication_changes():
    for aqi in (40, 150, 250, 350, 450):
        for lang in ("en", "hi"):
            core = r.rules_core(make_ctx(aqi, age="senior", conditions=["asthma"], lang=lang))
            assert not r.contains_forbidden_text(core)


def test_limit_exposure_heuristic():
    assert r.mentions_limit_exposure("Stay indoors today.", "en")
    assert r.mentions_limit_exposure("Limit time outdoors.", "en")
    assert not r.mentions_limit_exposure("Keep windows closed when the air outside is bad.", "en")
    assert r.mentions_limit_exposure("बाहर निकलना सीमित करें।", "hi")
    assert not r.mentions_limit_exposure("पानी खूब पिएं।", "hi")


# ---------------- best-time windows ----------------

def test_best_and_worst_windows_come_from_forecast():
    # Hours 18..23 then 00..05. Instant AQI dips around 22:00-00:00 and peaks at 20:00-22:00.
    vals = [250, 260, 270, 280, 150, 140, 145, 200, 240, 260, 270, 275]
    hours = [18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5]
    fc = [pt(h, v, v, day="2026-10-01" if h >= 18 else "2026-10-02") for h, v in zip(hours, vals)]
    text = r.compute_window_text(make_ctx(219, forecast=fc))
    # Lowest 2-hour average is hours 23 and 00 (142.5) -> wraps past midnight.
    assert "Best time: 23:00–01:00" in text
    # Highest is hours 20 and 21 (275).
    assert "Avoid 20:00–22:00" in text


def test_flat_forecast_says_no_time_is_better():
    fc = [pt(h, 175, 175) for h in range(8, 20)]
    assert "no time is clearly better" in r.compute_window_text(make_ctx(175, forecast=fc))
    assert r.compute_window_text(make_ctx(175, forecast=fc[:2])) is None  # too little data


def test_window_prefers_instant_values_over_smoothed():
    # Smoothed AQI is flat but instant AQI has a clear dip at 13:00-14:00.
    fc = [pt(h, 175, 300 if h not in (13, 14) else 120) for h in range(10, 20)]
    text = r.compute_window_text(make_ctx(175, forecast=fc))
    assert "Best time: 13:00–15:00" in text


# ---------------- safety layer ----------------

def good_ai(**overrides):
    core = {"risk_level": "High", "summary": "AQI is poor. Cut down time outdoors.",
            "do": ["Limit outdoor exposure.", "Keep windows closed."], "avoid": ["Outdoor exercise."],
            "mask": "n95", "exercise_advice": "Skip outdoor exercise today.", "best_time_window": "06:00-08:00"}
    core.update(overrides)
    return core


def test_valid_ai_advice_passes_through():
    ctx = make_ctx(219, age="child", conditions=["asthma"])
    out = r.enforce_safety(good_ai(), ctx, r.rules_core(ctx))
    assert out is not None and out["risk_level"] == "High" and out["mask"] == "n95"


def test_ai_cannot_downgrade_risk_below_rules_floor():
    ctx = make_ctx(219, age="child", conditions=["asthma"])
    assert r.enforce_safety(good_ai(risk_level="Low"), ctx, r.rules_core(ctx)) is None
    assert r.enforce_safety(good_ai(risk_level="Moderate"), ctx, r.rules_core(ctx)) is None


def test_ai_may_be_more_cautious_than_rules():
    ctx = make_ctx(219)  # rules: Moderate
    out = r.enforce_safety(good_ai(risk_level="High"), ctx, r.rules_core(ctx))
    assert out is not None and out["risk_level"] == "High"


def test_weak_mask_is_raised_to_rules_mask():
    ctx = make_ctx(219, age="child", conditions=["asthma"])
    out = r.enforce_safety(good_ai(mask="none"), ctx, r.rules_core(ctx))
    assert out["mask"] == "n95"


def test_limit_exposure_line_added_when_missing_at_very_poor():
    ctx = make_ctx(350)
    ai = good_ai(risk_level="Very High", do=["Drink water.", "Keep windows closed."])
    out = r.enforce_safety(ai, ctx, r.rules_core(ctx))
    assert any(r.mentions_limit_exposure(s, "en") for s in out["do"])
    # Not duplicated when the model already included it:
    ai2 = good_ai(risk_level="Very High", do=["Stay indoors today.", "Keep windows closed."])
    out2 = r.enforce_safety(ai2, ctx, r.rules_core(ctx))
    assert out2["do"] == ["Stay indoors today.", "Keep windows closed."]


def test_limit_exposure_also_triggered_by_instant_category():
    ctx = make_ctx(150, inst=350)  # official moderate, right-now very poor
    assert r.needs_limit_exposure(ctx)


def test_medication_advice_and_diagnosis_are_rejected():
    ctx = make_ctx(219, age="child", conditions=["asthma"])
    rules = r.rules_core(ctx)
    bad_texts = ["Stop taking your medicine today.", "You can skip your inhaler.",
                 "Reduce your dose on bad days.", "Take extra puffs of the inhaler.",
                 "This looks like a diagnosis of asthma."]
    for bad in bad_texts:
        assert r.enforce_safety(good_ai(summary=bad), ctx, rules) is None, bad
        assert r.enforce_safety(good_ai(do=[bad]), ctx, rules) is None, bad


def test_hindi_medication_advice_is_rejected():
    ctx = make_ctx(219, age="child", conditions=["asthma"], lang="hi")
    rules = r.rules_core(ctx)
    for bad in ("अपनी दवा बंद कर दें।", "इन्हेलर की खुराक बढ़ा दें।", "दवा लेना छोड़ दें।"):
        assert r.enforce_safety(good_ai(summary=bad), ctx, rules) is None, bad


def test_harmless_medication_mentions_are_allowed():
    ctx = make_ctx(219, age="child", conditions=["asthma"])
    rules = r.rules_core(ctx)
    ok = good_ai(do=["Keep your inhaler with you.", "Follow your doctor's usual advice."])
    assert r.enforce_safety(ok, ctx, rules) is not None


def test_ai_best_time_window_is_replaced_by_computed_window():
    fc = [pt(h, 200, 300 if h not in (13, 14) else 120) for h in range(10, 20)]
    ctx = make_ctx(219, forecast=fc)
    out = r.enforce_safety(good_ai(risk_level="Moderate", best_time_window="3 AM"), ctx, r.rules_core(ctx))
    assert "13:00–15:00" in out["best_time_window"]


def test_cache_key_ignores_instant_category_for_non_sensitive_users():
    a, b = make_ctx(219, inst=100), make_ctx(219, inst=450)
    assert r.cache_key(a) == r.cache_key(b)
    s1, s2 = make_ctx(219, inst=100, age="senior"), make_ctx(219, inst=450, age="senior")
    assert r.cache_key(s1) != r.cache_key(s2)


def test_profile_fingerprint_ignores_order_and_none():
    a = make_ctx(219, conditions=["copd", "asthma", "none"], routine=["outdoor_work", "commute_car"])
    b = make_ctx(219, conditions=["asthma", "copd"], routine=["commute_car", "outdoor_work"])
    assert r.fingerprint(a["profile"]) == r.fingerprint(b["profile"])
