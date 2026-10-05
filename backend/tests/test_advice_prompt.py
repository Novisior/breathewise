"""Prompt building and JSON extraction (pure Python)."""
import json

from app.services import advice_prompt as p
from app.text_utils import trim_sentences
from tests.test_advice_rules import make_ctx, pt


def test_extract_json_handles_fences_and_prose():
    assert p.extract_json('{"a": 1}') == {"a": 1}
    assert p.extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert p.extract_json('Here you go: {"a": {"b": 2}} Hope it helps!') == {"a": {"b": 2}}


def test_extract_json_rejects_garbage():
    for bad in ("", "no json here", "{broken", "[1, 2, 3]"):
        try:
            p.extract_json(bad)
        except ValueError:
            continue
        raise AssertionError(f"should have failed: {bad!r}")


def test_user_message_is_valid_json_with_minimums_and_data_only():
    fc = [pt(h, 200, 210) for h in range(8, 22)]  # 14 points -> only 12 sent
    ctx = make_ctx(219, inst=260, age="child", conditions=["asthma"], forecast=fc)
    msg = json.loads(p.build_user_message(ctx))
    assert msg["language"] == "en"
    assert msg["profile_is_sensitive"] is True
    assert msg["minimum_risk_level"] == "High" and msg["minimum_mask"] == "n95"
    assert msg["air"]["aqi"] == 219 and msg["air"]["aqi_instant_right_now"] == 260
    assert len(msg["air"]["forecast_next_12h"]) == 12


def test_system_prompt_contains_the_required_safety_rules():
    s = p.SYSTEM_PROMPT
    for needle in ("NOT a doctor", "Never diagnose", "medication", "limiting outdoor exposure",
                   "minimum_risk_level", "ONE JSON object", "At most 2 sentences", "Hindi"):
        assert needle in s, needle


def test_trim_sentences():
    assert trim_sentences("One. Two. Three.") == "One. Two."
    assert trim_sentences("PM2.5 is high. Stay in. Really.") == "PM2.5 is high. Stay in."
    assert trim_sentences("पहला वाक्य। दूसरा वाक्य। तीसरा वाक्य।") == "पहला वाक्य। दूसरा वाक्य।"
    assert trim_sentences("  spaced   out  text ") == "spaced out text"
