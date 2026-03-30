# Coal Equity Intelligence Dashboard

Self-updating dashboard for coal equity traders. Aggregates supply, demand, pricing, logistics, macro, company-specific, weather, and sentiment data streams that drive coal stock valuations.

## Quick Start

```bash
# 1. Copy config and add your API keys
cp config.example.yaml config.yaml
# Edit config.yaml with your API keys (EIA, FRED at minimum)

# 2. Run with Docker
docker compose up --build

# 3. Open dashboard
open http://localhost:5173
```

## API Keys (Free)

| Source | Get Key | Required For |
|--------|---------|--------------|
| **EIA** | [eia.gov/opendata/register.php](https://www.eia.gov/opendata/register.php) | US coal production, inventories, generation |
| **FRED** | [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html) | Henry Hub gas, AUD/USD, DXY, 10Y yield |
| **OilPriceAPI** | [oilpriceapi.com](https://www.oilpriceapi.com/) | Newcastle coal futures |
| **NewsAPI** | [newsapi.org/register](https://newsapi.org/register) | News sentiment (100 req/day free) |
| **Telegram** | [@BotFather](https://t.me/BotFather) | Alert delivery |

Optional: Reddit (PRAW), ENTSO-E, India CEA, ABS Australia.

## Running Without Docker

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Architecture

- **Backend**: Python 3.12 / FastAPI / APScheduler / SQLite (WAL mode)
- **Frontend**: React 18 / Vite / Tailwind CSS / Recharts
- **Database**: SQLite — single file at `data/coal_dashboard.db`

### Data Domains (8 modules)

| Domain | Key Data | Sources | Refresh |
|--------|----------|---------|---------|
| **Pricing** | Newcastle coal, Henry Hub gas, spreads | OilPriceAPI, EIA, FRED | 12min |
| **Supply** | US production, inventories, international | EIA, sxcoal, Indo HBA | Daily/Weekly |
| **Demand** | Power generation mix, steel production | EIA, ENTSO-E, World Steel | Daily |
| **Trade Flows** | US/Australia exports, freight | EIA, ABS, CSV upload | Monthly |
| **Macro** | AUD/USD, DXY, 10Y, PMI, COT | FRED, CFTC | Hourly |
| **Company** | Stock prices, financials, insider, 13F | yfinance, SEC EDGAR | 5min/Daily |
| **Weather** | HDD/CDD, ENSO, rainfall | NOAA, BOM Australia | 6hr |
| **Sentiment** | News, Reddit mentions, short interest | Google News RSS, PRAW | 30min |

### Watchlist

Primary: **BTU** (Peabody Energy), **WHC.AX** (Whitehaven Coal)

Secondary: CEIX, CNXR, HCC, AMR, ARLP, TGA.L, YAL.AX

## Dashboard Pages

- **Overview** — Watchlist heatmap, key prices, bull/bear signal board, alert feed
- **Pricing** — Coal benchmarks, gas prices, switching spreads
- **Supply** — US production, inventories, international supply
- **Demand** — Generation mix, steel production
- **Trade Flows** — Export/import data, world map (premium data via CSV upload)
- **Macro** — FX, rates, PMI, COT positioning
- **Company** — Deep dive per ticker: price chart, financials, insider activity, peer comparison
- **Weather** — HDD/CDD vs normal, ENSO status, mining region rainfall
- **Sentiment** — News feed with sentiment scoring, Reddit mentions, short interest

## Bull/Bear Signal Board

13 automated signals across all domains, updated every 30 minutes:

| Signal | Bull When | Bear When |
|--------|-----------|-----------|
| Newcastle vs 200-DMA | Price above | Price below |
| Gas/Coal Ratio | > 2.5 (gas expensive) | < 1.5 (gas cheap) |
| US Inventory | Below 5Y average | Above 5Y average |
| AUD/USD | Weakening (boosts WHC margins) | Strengthening |
| Insider Activity | Net buying 30d | Net selling |
| ENSO Phase | La Nina (supply risk) | - |
| News Sentiment | Score > 0.2 | Score < -0.2 |

## CSV Upload (Premium Data)

For data behind paywalls (Platts, Argus, Baltic Exchange), upload CSVs:

- **Met coal prices**: columns `date, benchmark, price_usd`
- **Freight rates**: columns `date, route, rate_usd`
- **Port stockpiles**: columns `date, port_name, stockpile_mt`

Upload via Settings page or `POST /api/upload?type=met_coal_prices`.

## Alerts

Configure threshold alerts via the Alerts page. Dispatches to Telegram.

Example alerts:
- Newcastle coal changes > 3% in 24 hours
- BTU stock moves > 5%
- Gas/coal ratio drops below 1.5
- Insider purchase > $100K

## API Endpoints

```
GET  /api/overview          # Aggregated dashboard snapshot
GET  /api/pricing/latest    # Current coal/gas prices
GET  /api/supply/summary    # Production + inventory snapshot
GET  /api/company/latest    # All watchlist stock prices
GET  /api/macro/latest      # FX, rates, PMI
GET  /api/system/health     # System status
GET  /api/system/freshness  # Data source freshness
POST /api/system/refresh/:domain  # Manual refresh
```

## Data Storage

All fetched data is stored locally in SQLite. Historical data enables trend analysis over 1W / 1M / 3M / 6M / 1Y / 3Y timeframes. Back up by copying `data/coal_dashboard.db`.
