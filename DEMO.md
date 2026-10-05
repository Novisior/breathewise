# BreatheWise: 5-minute demo script

**Before you start (2 min):** backend and frontend running, AI key set in `backend/.env` (the demo is still fine without it). Clear the site's data (DevTools → Application → Clear site data) so you start from onboarding. Use your phone, or Chrome DevTools in mobile mode at 375 px wide.

## 1. The problem (20 s)
"Air quality apps show a number. But what does *186* mean for a 62-year-old with asthma, versus a 25-year-old who cycles to work? BreatheWise turns the number into advice for you."

## 2. Onboarding (45 s)
- Pick **Senior**, tick **Asthma**, pick **Commute by bike or scooter**.
- Search your city and tap it. Point out that the dropdown closes and "Selected" appears.
- "Four taps. The profile stays on this phone and is never stored on a server."

## 3. The dashboard (60 s)
- **Gauge:** the AQI, its colour and category, the main pollutant. Mention "Right now" if it shows: the big number is the official 24-hour average, "right now" is the latest hour.
- **Advice card:** read the summary and the mask line. Watch the badge: *Standard guidance*, then *Personalising…*, then *Personalised by AI*. "Instant answer first, AI upgrade second, so you never wait on a spinner."
- Point at the amber disclaimer: "added by our code, never by the AI."

## 4. Best time to go out (45 s)
- Show the window and the hour strip. "Hourly forecast, daytime only. It will never tell you to jog at 3 AM."
- Point at the *Worst* line: "and when to stay in."
- Show the 48-hour chart, then tap a bar for the tooltip.

## 5. Safety, in one sentence (20 s)
"The AI's advice is checked by code against a rules table for this person's profile. It can be more careful than the rules, never less: if it is, we discard it or raise the mask advice."

## 6. Hindi (30 s)
- Tap **हिन्दी**. Everything switches, including the advice, which is re-requested in Hindi.
- "The rules fallback has full Hindi too."

## 7. Offline (45 s)
- Build and serve the PWA (`npm run build`, `npm run preview`), load the app once.
- DevTools → Network → tick **Offline**, reload.
- The app opens, shows your last data and an amber banner: *"You're offline. Showing saved data from 12 min ago."*
- Untick Offline: it refreshes by itself.

## 8. Be upfront about accuracy (30 s)
"The data is the CAMS satellite model, not a street monitor, so it can differ from the station near you. The next step is blending in real CPCB station data. We label the numbers as model estimates."

## If something goes wrong
| Symptom | Fix |
|---|---|
| Red error panel on load | Backend not running. Start it, then tap **Try again**. |
| Badge stays on "Standard guidance" | AI key missing, rate-limited or slow. The rules advice is the designed fallback. Run `python check_ai.py`. |
| Offline test shows an error | Use the **production** build. The service worker is off in `npm run dev`. |
| City not found | Try another spelling, or use "Use my current location". |
