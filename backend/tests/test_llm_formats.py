"""Provider request/response shapes (pure Python)."""
from app.services import llm_formats as f

MSGS = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "bad"},
        {"role": "user", "content": "again"}]


def test_gemini_request_shape():
    body = f.build_gemini("SYS", MSGS)
    assert body["systemInstruction"]["parts"][0]["text"] == "SYS"
    assert [c["role"] for c in body["contents"]] == ["user", "model", "user"]  # assistant -> model
    assert body["contents"][2]["parts"][0]["text"] == "again"
    assert body["generationConfig"]["responseMimeType"] == "application/json"


def test_gemini_response_parsing():
    ok = {"candidates": [{"content": {"parts": [{"text": '{"a":'}, {"text": "1}"}]}}]}
    assert f.parse_gemini(ok) == '{"a":1}'
    thought = {"candidates": [{"content": {"parts": [{"text": "thinking", "thought": True},
                                                     {"text": "answer"}]}}]}
    assert f.parse_gemini(thought) == "answer"
    assert f.parse_gemini({"candidates": [{"finishReason": "MAX_TOKENS"}]}) == ""  # empty -> retry upstream
    for bad in ({}, {"candidates": []}):
        try:
            f.parse_gemini(bad)
        except ValueError:
            continue
        raise AssertionError("should raise")


def test_openai_request_shape():
    body = f.build_openai("m1", "SYS", MSGS)
    assert body["model"] == "m1"
    assert body["messages"][0] == {"role": "system", "content": "SYS"}
    assert len(body["messages"]) == 4
    assert body["response_format"] == {"type": "json_object"}
    assert "response_format" not in f.build_openai("m1", "SYS", MSGS, json_mode=False)


def test_openai_response_parsing():
    assert f.parse_openai({"choices": [{"message": {"content": "{}"}}]}) == "{}"
    assert f.parse_openai({"choices": [{"message": {"content": None}}]}) == ""
    try:
        f.parse_openai({"choices": []})
    except ValueError:
        return
    raise AssertionError("should raise")


def test_anthropic_shapes():
    body = f.build_anthropic("m", "SYS", MSGS)
    assert body["system"] == "SYS" and len(body["messages"]) == 3
    assert f.parse_anthropic({"content": [{"type": "text", "text": "a"}, {"type": "tool_use"},
                                          {"type": "text", "text": "b"}]}) == "ab"


MODELS_LIST = {"models": [
    {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3.5-flash", "supportedGenerationMethods": ["generateContent", "countTokens"]},
    {"name": "models/gemini-3.1-flash-lite", "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3-flash-preview", "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3.1-flash-image", "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-2.5-flash-preview-tts", "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-embedding-001", "supportedGenerationMethods": ["embedContent"]},
    {"name": "models/gemini-3.5-pro", "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3.9-flash", "supportedGenerationMethods": ["predict"]},
]}


def test_usable_models_filters_out_non_chat_and_unsupported():
    names = f.usable_gemini_models(MODELS_LIST)
    assert set(names) == {"gemini-2.5-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite",
                          "gemini-3-flash-preview"}


def test_pick_prefers_newest_stable_non_lite():
    assert f.pick_gemini_model(MODELS_LIST) == "gemini-3.5-flash"


def test_pick_prefers_latest_alias_when_offered():
    data = {"models": MODELS_LIST["models"] + [
        {"name": "models/gemini-flash-latest", "supportedGenerationMethods": ["generateContent"]}]}
    assert f.pick_gemini_model(data) == "gemini-flash-latest"


def test_pick_version_comparison_is_numeric_not_textual():
    data = {"models": [
        {"name": "models/gemini-3.9-flash", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-3.10-flash", "supportedGenerationMethods": ["generateContent"]}]}
    assert f.pick_gemini_model(data) == "gemini-3.10-flash"


def test_pick_returns_none_when_nothing_usable():
    assert f.pick_gemini_model({}) is None
    assert f.pick_gemini_model({"models": [{"name": "models/embedding", "supportedGenerationMethods": []}]}) is None


def test_rank_orders_best_first_with_alias_on_top():
    ranked = f.rank_gemini_models(MODELS_LIST)
    # stable before preview; newer before older (numerically); non-lite before lite at equal version
    assert ranked == ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash",
                      "gemini-3-flash-preview"]
    data = {"models": MODELS_LIST["models"] + [
        {"name": "models/gemini-flash-latest", "supportedGenerationMethods": ["generateContent"]}]}
    assert f.rank_gemini_models(data)[0] == "gemini-flash-latest"
    assert f.rank_gemini_models({}) == []
