# BreatheWise

Live air quality for any city, turned into short, personal advice: should you go for that run, wear a mask, or wait until the evening?

- **Live AQI on India's CPCB scale**, with the main pollutant, weather and a 48-hour forecast.
- **Personalised advice** from your age group, health conditions and daily routine. Uses an AI model when configured, and always falls back to a built-in rules table, so it never shows a blank card.
- **Best-time planner:** the cleanest daytime two hours in the next 24, and the worst.
- **English and Hindi**, an installable app (PWA), and **offline mode** that shows the last saved data with a clear banner.

```
breathewise/
├── backend/    FastAPI: AQI maths, Open-Meteo data, advice (AI + rules + safety checks)
└── frontend/   React + Vite + Tailwind + Recharts (PWA)
```

## Run it (Windows Command Prompt)

You need **Python 3.11+** and **Node.js 18+**. Open two Command Prompt windows.

**Window 1: backend**

```
cd breathewise\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Check http://127.0.0.1:8000/api/health. It should return `{"status":"ok", ...}`.

**Window 2: frontend**

```
cd breathewise\frontend
npm install
npm run dev
```

Open http://localhost:5173.

macOS / Linux: the same, except `source .venv/bin/activate` and `cp .env.example .env`.

The app works with no AI key at all (rules-based advice). To turn on AI advice, edit `backend/.env`, set `AI_PROVIDER` and `AI_API_KEY` (see the comments in `.env.example`), restart the backend, and run `python check_ai.py` to confirm the key works. **Never commit `.env` or share it.**

## How the pieces fit

| Endpoint | What it does |
|---|---|
| `GET /api/air?lat=&lon=` | AQI (CPCB), pollutants, weather, 48 h forecast. Cached 15 min per ~1 km. |
| `GET /api/geocode?q=&lang=` | City search (Open-Meteo geocoding). |
| `POST /api/advice` | Advice for a profile + air data. `use_ai:false` returns the rules answer instantly; `use_ai:true` asks the AI. |
| `GET /api/health` | Status, and whether AI is configured. |

How advice works:

1. The app asks for the **rules answer first** (instant), then asks again for the **AI upgrade**. If the AI is slow, down or rejected, the rules answer simply stays.
2. AI output is validated, then checked by code (**safety layer**). The AI may be *more* cautious than the rules, never less: advice with forbidden medical wording, or a risk level below the rules' floor for that person, is discarded in favour of the rules answer; a weaker mask is raised to the rules' mask; for Very Poor / Severe air a "limit outdoor exposure" line is added; and the best-time text is replaced by one computed from the forecast.
3. The medical **disclaimer is added by code**, never by the model.

## Accuracy: what the numbers are and are not

- The AQI maths follows the **CPCB (2014)** breakpoints, using 24-hour averages for PM2.5, PM10, NO₂ and SO₂ and 8-hour averages for O₃ and CO. **Please verify the breakpoint table in `backend/app/aqi.py` against CPCB's official publication before relying on it.**
- The **data is a model, not a ground station.** Open-Meteo's air data comes from the CAMS global model (coarse grid, roughly 40 km). It can read lower or higher than the monitor nearest you. The app says "model estimate" where it matters.
- The big number is the **24-hour average**. The planner and chart use **hourly** values, because an average would hide the cleaner hours. Both are labelled.
- Other apps often show the **US AQI** scale, which gives lower numbers than CPCB for the same air (PM2.5 of 100 µg/m³ is about 232 on CPCB and about 174 on the US scale).
- A future improvement is real station readings (for example OpenAQ's CPCB stations) with the model as fallback.

## Offline and install

- The app shell is cached by a service worker, so it opens offline. Air data and advice are **not** cached by the service worker. Instead the app keeps its own "last good" copy, shown with a banner ("Showing data from 20 min ago"), and only for the same location.
- Hours that have already passed are removed from saved data, so the planner never suggests a time in the past.
- The service worker only runs in a **production build**: `npm run build`, then `npm run preview`. In Chrome or Edge, open the preview URL, use the install icon in the address bar, and test offline by ticking **Offline** in DevTools → Network.
- To deploy, serve `frontend/dist` over HTTPS and set `VITE_API_BASE` to the backend URL before building. Add that site's origin to `CORS_ORIGINS` in the backend `.env`.

## Tests

```
cd backend && pytest          # AQI maths, advice rules, safety layer, API (mocked upstream)
cd frontend && npm test       # best-time planner and past-hour filtering
```

## Privacy

Your profile and location are stored **in your browser only** (localStorage). Coordinates are rounded to about 1 km. The profile is sent to the backend with each advice request so it can be personalised, and the backend logs only high-level events, not profiles. If AI advice is on, the age group, conditions, routine and current air readings are sent to your chosen AI provider.

## Known limits

- Hindi text was written by an AI assistant. **Have a native speaker review it, especially the health wording, before any public demo.** The backend's own Hindi fallback advice needs the same review.
- Not medical advice. The app says so on screen and in every advice response.
- Notifications, comparing locations and a symptom diary are not built.
