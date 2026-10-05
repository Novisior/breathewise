"""
Quick check that your AI provider + key work, and how FAST each model is.

Put this file in the `backend` folder (next to `.env`), then run:
    python check_ai.py         -> test the app's normal flow
    python check_ai.py speed   -> (Gemini) time the top models one by one, to choose AI_MODEL
It never prints your key.
"""
import asyncio
import dataclasses
import sys
import time

from app.services import llm
from app.services import llm_formats as fmt

HINTS = {
    "HTTP 400": "The request was rejected. Usually a wrong AI_MODEL name for this provider.",
    "HTTP 401": "The key was not accepted. Re-copy AI_API_KEY (no quotes, no spaces).",
    "HTTP 403": "Access denied. The key may be for another service, disabled, or the API "
                "is not available for your account/region. Create a fresh key.",
    "HTTP 404": "Model not found. Set AI_MODEL to a model name your provider currently lists.",
    "HTTP 429": "Rate limit or free quota reached. Wait a minute and try again, or use another model.",
    "HTTP 503": "The provider is overloaded right now. Try again, or pick another model (python check_ai.py speed).",
    "timeout": "No answer in time. The model may be slow: try `python check_ai.py speed` and set a faster AI_MODEL.",
    "network error": "Could not connect. Check your internet connection, VPN or firewall.",
}
PROMPT = [{"role": "user", "content": 'Return exactly this JSON: {"ok": true}'}]
SPEED_TEST_MODELS = 8        # how many models to time
SPEED_TEST_TIMEOUT = 15      # seconds allowed per model


async def timed_chat() -> tuple[str | None, str | None, float]:
    start = time.monotonic()
    try:
        reply = await llm.chat("Reply with JSON only.", PROMPT)
        return reply, None, time.monotonic() - start
    except llm.LLMError as e:
        return None, str(e), time.monotonic() - start


async def amain() -> None:
    # Everything runs inside ONE event loop: the HTTP client cannot be shared across loops.
    st = llm.status()
    print("Settings seen by the app:", st, flush=True)
    if not st["configured"]:
        print("\nNOT CONFIGURED:", st["problem"])
        print("Edit backend\\.env, save it, and run this again.")
        return

    models: list[str] = []
    if st["provider"] == "gemini":
        try:
            models = fmt.rank_names(await llm.list_gemini_models())
            print("\nGemini models your key can use (best first):", ", ".join(models) or "(none found)", flush=True)
        except llm.LLMError as e:
            print(f"\nCould not list Gemini models: {e}", flush=True)

    try:
        if "speed" in sys.argv[1:] and models:
            to_test = models[:SPEED_TEST_MODELS]
            print(f"\nTiming {len(to_test)} models, one short call each "
                  f"(up to {SPEED_TEST_TIMEOUT}s per model)...", flush=True)
            original = llm.settings
            results = []
            for m in to_test:
                llm.settings = dataclasses.replace(original, ai_model=m, ai_timeout=SPEED_TEST_TIMEOUT)
                reply, err, secs = await timed_chat()
                ok = reply is not None
                results.append((m, ok, secs))
                print(f"  {m:<32} " + (f"OK in {secs:.1f}s" if ok else f"FAILED ({err}) after {secs:.1f}s"), flush=True)
            llm.settings = original
            working = sorted((r for r in results if r[1]), key=lambda r: r[2])
            if working:
                print(f"\nFastest working model: {working[0][0]} ({working[0][2]:.1f}s)")
                print(f"Put this in backend\\.env:   AI_MODEL={working[0][0]}")
            else:
                print("\nNo model worked. Try again in a minute, or check the hints above.")
            return

        print("\nCalling the AI the way the app does (this can take a few seconds)...", flush=True)
        reply, err, secs = await timed_chat()
        if err:
            print(f"\nFAILED after {secs:.1f}s: {err}")
            for key, hint in HINTS.items():
                if key in err:
                    print("Hint:", hint)
            return
        print(f"\nSUCCESS in {secs:.1f}s. The model replied:", reply.strip()[:200])
        print("Model used:", llm.status()["model"])
        if secs > 8:
            print("That is slow for a web app. Run `python check_ai.py speed` and pick a faster AI_MODEL.")
    finally:
        await llm.aclose()


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
