# Wind Forecast Monitor – UK day-ahead buying support

Web app that helps a UK energy-utility buying team (1) see the **latest wind forecast available at the
day-ahead decision time** and (2) **quantify how wrong that forecast tends to be**, using Elexon data only
(national `WIND` actuals from **FUELHH**, forecasts from **WINDFOR**) for **purchase decisions made in January 2026**.

**Live app:** `<add your Vercel URL here>`  ·  **Demo video:** `<add unlisted YouTube link here>`

> **AI disclosure:** this project was built with AI assistance (Claude by Anthropic) for scaffolding, code and documentation.
> All design decisions, and the final code, were reviewed by the author.

## How the problem is modelled
| Item | Choice |
|---|---|
| Decision | Buying on day **D-1** for delivery on day **D** (decision dates 1–31 Jan 2026 → delivery 2 Jan–1 Feb) |
| Decision time | Configurable gate time on D-1, default **09:00 UK time** (UTC = UK time in January) |
| "Forecast at decision time" | For each half-hour target, the **latest forecast with `publishTime` ≤ decision time** |
| Error | `forecast − actual` in MW. Positive = wind over-forecast → buyer short; negative = over-bought |
| Metrics | MAE, RMSE, bias, MAPE, normalised MAE, P50/P90/P95 absolute error, P10/P90 signed error |
| Uncertainty band | Actual ≈ forecast − error, so the P10–P90 of historical errors gives a likely range around each forecast. P90 of the signed error is shown as the **extra MW to plan for** |
| Horizon analysis | Every January forecast grouped by hours between `publishTime` and `startTime` (6h buckets, 0–48h) |

Assumption to confirm with the client: the day-ahead gate closure time (default 09:00 is changeable in the UI).

## Repository layout
```
backend/
  app/elexon.py      Elexon API client (FUELHH + WINDFOR streams, chunked requests)
  app/data.py        Snapshot loading + Dataset (fast "latest forecast before cutoff" lookup)
  app/analysis.py    All metrics / aggregations (pure Python, unit-tested)
  app/main.py        FastAPI routes: /api/meta /api/decision /api/accuracy /api/horizon (+ serves the UI)
  scripts/fetch_data.py   Downloads January data into backend/data/wind_jan2026.json
  tests/             pytest unit tests
  data/              data snapshot (committed so the deployed app needs no live calls)
frontend/            React + Vite + Recharts UI
api/index.py         Vercel serverless entry (imports the FastAPI app)
Dockerfile, docker-compose.yml, vercel.json
```

## Run it
**1. Get the data (once, needs internet):**
```bash
cd backend && pip install -r requirements.txt
python -m scripts.fetch_data          # writes data/wind_jan2026.json  → commit this file
```
(If you skip this, the backend fetches live from Elexon on first request and caches it in a temp folder.)

**2. Docker (single container, UI + API on :8000):**
```bash
docker compose up --build        # open http://localhost:8000
```

**3. Local dev:**
```bash
cd backend && uvicorn app.main:app --reload          # API on :8000
cd frontend && npm install && npm run dev            # UI on :5173 (proxies /api)
cd backend && python -m pytest                       # tests
```

## Deploy to Vercel
1. Run the fetch script and commit `backend/data/wind_jan2026.json`.
2. Push to a public GitHub repo with an anonymous name, import it in Vercel (framework: *Other*). `vercel.json` handles
   the React build and the Python function.
3. Open the URL in an incognito window to confirm it loads.

## Design notes
- **Snapshot over live calls:** Elexon is only needed once; the app serves a frozen January dataset, so it is fast, reproducible and demo-safe.
- **No pandas:** ~35k forecast rows fit in memory; pure Python keeps the Vercel bundle tiny and the maths easy to audit.
- **Vintage-aware:** forecasts are never joined naively on `startTime`; the `publishTime` ≤ decision-time rule avoids look-ahead leakage.
- **Limitations:** single national series; default gate time is an assumption; no weather inputs; UK local time == UTC in January (would need tz handling for summer months).
