# BreatheWise frontend (Phase 3)

React + Vite + Tailwind + Recharts. Talks to the FastAPI backend in `../backend`.

## Run

```bash
# terminal 1: backend
cd backend && uvicorn app.main:app --reload        # http://127.0.0.1:8000

# terminal 2: frontend
cd frontend && npm install && npm run dev          # http://localhost:5173
```

In dev, Vite proxies `/api/*` to the backend (see `vite.config.js`), so no CORS setup is needed.
For production set `VITE_API_BASE` (see `.env.example`).

`npm test` runs the best-time planner unit tests (Node's built-in runner, no extra packages).

## Layout

- `src/lib/`: `api.js` (typed errors, timeouts), `hooks.js` (`useAir`, `useAdvice`), `bestWindow.js` (planner maths), `aqiColors.js`, `storage.js`
- `src/components/`: Onboarding, LocationSearch, Hero, AdviceCard, BestTimePlanner, ForecastChart, PollutantGrid, WhyItMatters, Skeletons, ErrorStates
- `src/i18n/`: `en.json` + `useT.jsx`. Every visible string goes through `t()`; Phase 4 adds `hi.json` and the toggle.

## Behaviour worth knowing

- Advice loads in two steps: instant rules-based answer (`use_ai:false`), then an upgrade (`use_ai:true`). If the upgrade fails, the first answer stays.
- Headline AQI is the backend's 24-hour-averaged CPCB value. The planner and chart use the hourly `aqi_instant`, and the UI says so.
- Profile and location live in `localStorage` only. Coordinates are rounded to 2 decimals (~1 km).
