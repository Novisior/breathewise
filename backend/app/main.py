"""BreatheWise backend: FastAPI app. Run with:  uvicorn app.main:app --reload"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.aqi import InsufficientDataError
from app.cache import TTLCache
from app.config import settings
from app.models import AdviceRequest, AdviceResponse, AirResponse, GeocodeResponse
from app.services import advice, llm, openmeteo
from app.services.air_builder import build_air_payload, normalize_geocode

# Log only high-level events; never request headers, keys, or user profiles.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("breathewise")

air_cache = TTLCache(settings.air_cache_ttl)
geocode_cache = TTLCache(settings.geocode_cache_ttl)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # One shared HTTP client (connection reuse) with a hard timeout on every call.
    app.state.http = httpx.AsyncClient(
        timeout=settings.http_timeout, headers={"User-Agent": "BreatheWise/0.1"}
    )
    st = llm.status()
    if st["configured"]:
        log.info("AI advice ON: provider=%s model=%s", st["provider"], st["model"])
    else:
        log.warning("AI advice OFF (rules-only). %s", st["problem"])
    yield
    await app.state.http.aclose()
    await llm.aclose()


app = FastAPI(title="BreatheWise API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "ai": llm.status()}


@app.get("/api/air", response_model=AirResponse)
async def get_air(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
):
    # Round to 2 decimals (~1 km): nearby requests share one cache entry.
    key = (round(lat, 2), round(lon, 2))
    cached = air_cache.get(key)
    if cached is not None:
        return cached

    client = app.state.http
    # Air data is essential; weather is a bonus, so its failure is tolerated.
    air_res, weather_res = await asyncio.gather(
        openmeteo.fetch_air(client, lat, lon),
        openmeteo.fetch_weather(client, lat, lon),
        return_exceptions=True,
    )
    if isinstance(air_res, openmeteo.UpstreamError):
        log.warning("Air fetch failed: %s", air_res)
        raise HTTPException(status_code=502, detail=str(air_res))
    if isinstance(air_res, BaseException):
        raise air_res
    weather = None if isinstance(weather_res, BaseException) else weather_res
    if isinstance(weather_res, BaseException):
        log.warning("Weather fetch failed (continuing without it): %s", weather_res)

    try:
        payload = build_air_payload(
            air_res, weather, lat, lon,
            updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
    except InsufficientDataError:
        raise HTTPException(
            status_code=502, detail="Not enough air quality data for this location yet."
        ) from None

    air_cache.set(key, payload)
    return payload


@app.get("/api/geocode", response_model=GeocodeResponse)
async def geocode(
    q: str = Query(..., min_length=2, max_length=80),
    lang: Literal["en", "hi"] = "en",
):
    q = q.strip()
    if len(q) < 2:
        raise HTTPException(status_code=422, detail="Search text is too short.")
    key = (q.lower(), lang)
    cached = geocode_cache.get(key)
    if cached is not None:
        return cached

    try:
        raw = await openmeteo.search_city(app.state.http, q, lang)
    except openmeteo.UpstreamError as e:
        raise HTTPException(status_code=502, detail=str(e)) from None

    result = {"results": normalize_geocode(raw)}
    geocode_cache.set(key, result)
    return result


@app.post("/api/advice", response_model=AdviceResponse)
async def post_advice(req: AdviceRequest):
    """Personalised advice. Uses Claude when a key is set, otherwise (or on any failure) the rules table."""
    return await advice.get_advice(req)
