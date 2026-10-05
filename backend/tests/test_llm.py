"""Transport layer tests using httpx's MockTransport: no real network, no real key."""
import asyncio
import dataclasses
import json

import httpx
import pytest

from app.config import settings
from app.services import llm

KEY = "TEST-SECRET-KEY"


def configure(monkeypatch, handler, provider="gemini", model="", base_url="", key=KEY):
    s = dataclasses.replace(settings, ai_provider=provider, ai_api_key=key,
                            ai_model=model, ai_base_url=base_url)
    monkeypatch.setattr(llm, "settings", s)
    monkeypatch.setattr(llm, "_gemini_ranked", [])
    monkeypatch.setattr(llm, "RETRY_DELAY", 0)  # tests must not sleep
    monkeypatch.setattr(llm, "_http", httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def chat():
    return asyncio.run(llm.chat("SYS", [{"role": "user", "content": "hi"}]))


def test_is_configured(monkeypatch):
    def check(**kw):
        monkeypatch.setattr(llm, "settings", dataclasses.replace(settings, **kw))
        return llm.is_configured()
    assert check(ai_provider="none", ai_api_key="k") is False
    assert check(ai_provider="gemini", ai_api_key="") is False
    assert check(ai_provider="gemini", ai_api_key="k") is True
    assert check(ai_provider="groq", ai_api_key="k") is True
    assert check(ai_provider="openai_compatible", ai_api_key="k", ai_base_url="", ai_model="") is False
    assert check(ai_provider="openai_compatible", ai_api_key="k",
                 ai_base_url="https://api.x.ai/v1", ai_model="some-model") is True
    assert check(ai_provider="skynet", ai_api_key="k") is False


MODELS = {"models": [
    {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3.5-flash", "supportedGenerationMethods": ["generateContent"]},
]}
OK_REPLY = {"candidates": [{"content": {"parts": [{"text": '{"ok": 1}'}]}}]}


def test_gemini_auto_detects_model_and_sends_key_in_header(monkeypatch):
    seen = {"posts": [], "gets": 0}

    def handler(request: httpx.Request):
        assert request.headers.get("x-goog-api-key") == KEY and KEY not in str(request.url)
        if request.method == "GET":
            seen["gets"] += 1
            return httpx.Response(200, json=MODELS)
        seen["posts"].append(str(request.url))
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=OK_REPLY)

    configure(monkeypatch, handler, "gemini")
    assert chat() == '{"ok": 1}'
    assert chat() == '{"ok": 1}'
    assert seen["posts"][0].endswith("/models/gemini-3.5-flash:generateContent")
    assert seen["gets"] == 1  # discovery result is cached
    assert seen["body"]["systemInstruction"]["parts"][0]["text"] == "SYS"


def test_explicit_model_skips_discovery(monkeypatch):
    methods = []

    def handler(request):
        methods.append(request.method)
        return httpx.Response(200, json=OK_REPLY)

    configure(monkeypatch, handler, "gemini", model="my-model")
    chat()
    assert methods == ["POST"]


def test_discovery_failure_falls_back_to_default_model(monkeypatch):
    urls = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(500)
        urls.append(str(request.url))
        return httpx.Response(200, json=OK_REPLY)

    configure(monkeypatch, handler, "gemini")
    assert chat() == '{"ok": 1}'
    assert urls[0].endswith(f"/models/{llm.DEFAULT_MODELS['gemini']}:generateContent")


def test_auto_model_that_returns_404_is_rediscovered_once(monkeypatch):
    state = {"lists": 0, "posts": []}

    def handler(request):
        if request.method == "GET":
            state["lists"] += 1
            name = "gemini-old-flash" if state["lists"] == 1 else "gemini-3.5-flash"
            return httpx.Response(200, json={"models": [
                {"name": f"models/{name}", "supportedGenerationMethods": ["generateContent"]}]})
        state["posts"].append(str(request.url))
        if "gemini-old-flash" in str(request.url):
            return httpx.Response(404)
        return httpx.Response(200, json=OK_REPLY)

    configure(monkeypatch, handler, "gemini")
    assert chat() == '{"ok": 1}'
    assert len(state["posts"]) == 2 and state["posts"][1].endswith("gemini-3.5-flash:generateContent")


def test_explicit_model_404_is_not_retried(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request.method)
        return httpx.Response(404)

    configure(monkeypatch, handler, "gemini", model="gone-model")
    with pytest.raises(llm.LLMError, match="404"):
        chat()
    assert calls == ["POST"]


def test_groq_call_uses_bearer_header_and_json_mode(monkeypatch):
    seen = {}

    def handler(request):
        seen["url"], seen["auth"] = str(request.url), request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    configure(monkeypatch, handler, "groq")
    assert chat() == "{}"
    assert seen["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert seen["auth"] == f"Bearer {KEY}"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert seen["body"]["model"]  # default model filled in


def test_openai_compatible_uses_custom_base_url_and_model(monkeypatch):
    seen = {}

    def handler(request):
        seen["url"], seen["body"] = str(request.url), json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "hello"}}]})

    configure(monkeypatch, handler, "openai_compatible", model="grok-x", base_url="https://api.x.ai/v1/")
    assert chat() == "hello"
    assert seen["url"] == "https://api.x.ai/v1/chat/completions"
    assert seen["body"]["model"] == "grok-x"


def test_json_mode_rejected_with_400_is_retried_without_it(monkeypatch):
    bodies = []

    def handler(request):
        body = json.loads(request.content)
        bodies.append(body)
        if "response_format" in body:
            return httpx.Response(400, json={"error": "response_format unsupported"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    configure(monkeypatch, handler, "groq")
    assert chat() == "{}"
    assert len(bodies) == 2 and "response_format" not in bodies[1]


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500, 503])
def test_http_errors_become_llm_error_without_leaking_secrets(monkeypatch, status):
    configure(monkeypatch, lambda r: httpx.Response(status, text=f"oops {KEY} echoed"), "gemini")
    with pytest.raises(llm.LLMError) as err:
        chat()
    assert str(status) in str(err.value) and KEY not in str(err.value)


def test_timeout_and_network_errors(monkeypatch):
    def timeout(request):
        raise httpx.ReadTimeout("slow")

    def down(request):
        raise httpx.ConnectError("down")

    configure(monkeypatch, timeout, "groq")
    with pytest.raises(llm.LLMError, match="timeout"):
        chat()
    configure(monkeypatch, down, "groq")
    with pytest.raises(llm.LLMError, match="network"):
        chat()


def test_garbage_responses_become_llm_error(monkeypatch):
    configure(monkeypatch, lambda r: httpx.Response(200, text="<html>not json</html>"), "gemini")
    with pytest.raises(llm.LLMError):
        chat()
    configure(monkeypatch, lambda r: httpx.Response(200, json={"candidates": []}), "gemini")
    with pytest.raises(llm.LLMError):
        chat()


def test_unconfigured_raises(monkeypatch):
    monkeypatch.setattr(llm, "settings", dataclasses.replace(settings, ai_provider="none"))
    with pytest.raises(llm.LLMError):
        chat()


def test_status_explains_what_is_wrong(monkeypatch):
    def st(**kw):
        monkeypatch.setattr(llm, "settings", dataclasses.replace(settings, **kw))
        out = llm.status()
        assert "key" not in " ".join(str(v) for v in out.values()).lower() or out["problem"]  # no key leaked
        return out
    assert "not set" in st(ai_provider="none")["problem"]
    assert "not valid" in st(ai_provider="gemni", ai_api_key="k")["problem"]
    assert "AI_API_KEY is empty" in st(ai_provider="gemini", ai_api_key="")["problem"]
    assert "AI_BASE_URL" in st(ai_provider="openai_compatible", ai_api_key="k")["problem"]
    ok = st(ai_provider="gemini", ai_api_key="SECRET")
    assert ok["configured"] is True and ok["problem"] is None and "SECRET" not in str(ok)


TWO_MODELS = {"models": [
    {"name": "models/gemini-3.5-flash", "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3.1-flash-lite", "supportedGenerationMethods": ["generateContent"]},
]}


def test_busy_gemini_model_falls_back_to_next_best_model(monkeypatch):
    posts = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json=TWO_MODELS)
        posts.append(str(request.url))
        return httpx.Response(503) if "gemini-3.5-flash:" in str(request.url) else httpx.Response(200, json=OK_REPLY)

    configure(monkeypatch, handler, "gemini")
    assert chat() == '{"ok": 1}'
    assert posts[0].endswith("gemini-3.5-flash:generateContent")
    assert posts[1].endswith("gemini-3.1-flash-lite:generateContent")


def test_all_models_busy_raises_after_bounded_tries(monkeypatch):
    posts = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json=TWO_MODELS)
        posts.append(1)
        return httpx.Response(503)

    configure(monkeypatch, handler, "gemini")
    with pytest.raises(llm.LLMError, match="503"):
        chat()
    assert len(posts) == 2  # both candidates tried, then give up


def test_explicit_model_is_retried_once_on_503(monkeypatch):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503) if calls["n"] == 1 else httpx.Response(200, json=OK_REPLY)

    configure(monkeypatch, handler, "gemini", model="fixed-model")
    assert chat() == '{"ok": 1}'
    assert calls["n"] == 2


def test_explicit_model_503_twice_gives_up(monkeypatch):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503)

    configure(monkeypatch, handler, "gemini", model="fixed-model")
    with pytest.raises(llm.LLMError, match="503"):
        chat()
    assert calls["n"] == 2


def test_groq_busy_is_retried_once(monkeypatch):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    configure(monkeypatch, handler, "groq")
    assert chat() == "{}"
    assert calls["n"] == 2


def test_slow_model_times_out_then_next_model_is_used_and_slow_one_is_demoted(monkeypatch):
    posts = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json=TWO_MODELS)
        posts.append(str(request.url))
        if "gemini-3.5-flash:" in str(request.url):
            raise httpx.ReadTimeout("too slow")
        return httpx.Response(200, json=OK_REPLY)

    configure(monkeypatch, handler, "gemini")
    assert chat() == '{"ok": 1}'
    assert posts[0].endswith("gemini-3.5-flash:generateContent")
    assert posts[1].endswith("gemini-3.1-flash-lite:generateContent")
    assert llm._gemini_ranked[0] == "gemini-3.1-flash-lite"   # fast one now goes first
    assert llm._gemini_ranked[-1] == "gemini-3.5-flash"


def test_every_model_timing_out_raises_timeout(monkeypatch):
    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json=TWO_MODELS)
        raise httpx.ReadTimeout("too slow")

    configure(monkeypatch, handler, "gemini")
    with pytest.raises(llm.LLMError, match="timeout"):
        chat()


def test_fixed_model_timeout_is_not_retried(monkeypatch):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        raise httpx.ReadTimeout("too slow")

    configure(monkeypatch, handler, "gemini", model="fixed-model")
    with pytest.raises(llm.LLMError, match="timeout"):
        chat()
    assert calls["n"] == 1


def test_aclose_closes_and_resets_the_shared_client(monkeypatch):
    configure(monkeypatch, lambda r: httpx.Response(200, json=OK_REPLY), "gemini", model="m")
    chat()
    asyncio.run(llm.aclose())
    assert llm._http is None
