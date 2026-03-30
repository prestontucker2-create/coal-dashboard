import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import load_config, AppConfig
from database import DatabaseManager
from scheduler import create_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Global state
_config: AppConfig = None
_db: DatabaseManager = None
_scheduler = None
_http_client: httpx.AsyncClient = None
_orchestrators: dict = {}


def get_db() -> DatabaseManager:
    return _db


def get_config() -> AppConfig:
    return _config


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _config, _db, _scheduler, _http_client, _orchestrators

    # 1. Load config
    _config = load_config()
    logger.info(f"Config loaded. Watchlist: {[w.ticker for w in _config.watchlist]}")

    # 2. Init database
    _db = DatabaseManager(_config.database.path)
    await _db.init()
    logger.info("Database initialized")

    # 3. Create HTTP client
    _http_client = httpx.AsyncClient(
        timeout=30.0,
        headers={"User-Agent": "CoalDashboard/1.0 (contact@example.com)"},
    )

    # 4. Create scheduler
    _scheduler = create_scheduler()

    # 5. Register domain orchestrators
    await _register_domains()

    # 6. Register alert and signal engines
    from scheduler import register_domain_job
    try:
        from services.alerts import AlertEngine
        from services.signals import SignalEngine

        alert_engine = AlertEngine(_db, _config)
        signal_engine = SignalEngine(_db)

        register_domain_job(_scheduler, "alert_evaluator", alert_engine.evaluate_all, 60)
        register_domain_job(_scheduler, "signal_board", signal_engine.compute_all, 1800)
        logger.info("Alert and signal engines registered")
    except Exception as e:
        logger.warning(f"Failed to register alert/signal engines: {e}")

    # 7. Start scheduler
    _scheduler.start()
    logger.info("Scheduler started")

    yield

    # Shutdown
    _scheduler.shutdown()
    await _http_client.aclose()
    await _db.close()
    logger.info("Shutdown complete")


async def _register_domains():
    from scheduler import register_domain_job

    # Import and register each domain
    try:
        from domains.company.fetcher import CompanyFetcher
        from domains.company.processor import CompanyProcessor
        from domains.company.storage import CompanyStorage
        from domains.base import DomainOrchestrator

        fetcher = CompanyFetcher(_config.__dict__, _http_client)
        processor = CompanyProcessor()
        storage = CompanyStorage(_db)
        orch = DomainOrchestrator(fetcher, processor, storage, "stock_prices", "company", _db)
        _orchestrators["stock_prices"] = orch

        register_domain_job(
            _scheduler, "stock_prices_daily",
            orch.run, _config.refresh_intervals.stock_prices_daily,
        )
        logger.info("Company domain registered")
    except Exception as e:
        logger.warning(f"Failed to register company domain: {e}")

    try:
        from domains.pricing.fetcher import PricingFetcher
        from domains.pricing.processor import PricingProcessor
        from domains.pricing.storage import PricingStorage

        fetcher = PricingFetcher(_config.__dict__, _http_client)
        processor = PricingProcessor()
        storage = PricingStorage(_db)
        orch = DomainOrchestrator(fetcher, processor, storage, "coal_benchmarks", "pricing", _db)
        _orchestrators["coal_benchmarks"] = orch

        register_domain_job(
            _scheduler, "coal_benchmarks",
            orch.run, _config.refresh_intervals.coal_benchmarks,
        )
        logger.info("Pricing domain registered")
    except Exception as e:
        logger.warning(f"Failed to register pricing domain: {e}")

    try:
        from domains.supply.fetcher import SupplyFetcher
        from domains.supply.processor import SupplyProcessor
        from domains.supply.storage import SupplyStorage

        fetcher = SupplyFetcher(_config.__dict__, _http_client)
        processor = SupplyProcessor()
        storage = SupplyStorage(_db)
        orch = DomainOrchestrator(fetcher, processor, storage, "eia_supply", "supply", _db)
        _orchestrators["eia_supply"] = orch

        register_domain_job(
            _scheduler, "eia_supply",
            orch.run, _config.refresh_intervals.eia_weekly,
        )
        logger.info("Supply domain registered")
    except Exception as e:
        logger.warning(f"Failed to register supply domain: {e}")

    try:
        from domains.macro.fetcher import MacroFetcher
        from domains.macro.processor import MacroProcessor
        from domains.macro.storage import MacroStorage

        fetcher = MacroFetcher(_config.__dict__, _http_client)
        processor = MacroProcessor()
        storage = MacroStorage(_db)
        orch = DomainOrchestrator(fetcher, processor, storage, "fred_macro", "macro", _db)
        _orchestrators["fred_macro"] = orch

        register_domain_job(
            _scheduler, "fred_macro",
            orch.run, _config.refresh_intervals.fred_macro,
        )
        logger.info("Macro domain registered")
    except Exception as e:
        logger.warning(f"Failed to register macro domain: {e}")

    try:
        from domains.demand.fetcher import DemandFetcher
        from domains.demand.processor import DemandProcessor
        from domains.demand.storage import DemandStorage

        fetcher = DemandFetcher(_config.__dict__, _http_client)
        processor = DemandProcessor()
        storage = DemandStorage(_db)
        orch = DomainOrchestrator(fetcher, processor, storage, "demand_data", "demand", _db)
        _orchestrators["demand_data"] = orch

        register_domain_job(
            _scheduler, "demand_data",
            orch.run, _config.refresh_intervals.eia_weekly,
        )
        logger.info("Demand domain registered")
    except Exception as e:
        logger.warning(f"Failed to register demand domain: {e}")

    try:
        from domains.weather.fetcher import WeatherFetcher
        from domains.weather.processor import WeatherProcessor
        from domains.weather.storage import WeatherStorage

        fetcher = WeatherFetcher(_config.__dict__, _http_client)
        processor = WeatherProcessor()
        storage = WeatherStorage(_db)
        orch = DomainOrchestrator(fetcher, processor, storage, "weather_data", "weather", _db)
        _orchestrators["weather_data"] = orch

        register_domain_job(
            _scheduler, "weather_data",
            orch.run, _config.refresh_intervals.weather,
        )
        logger.info("Weather domain registered")
    except Exception as e:
        logger.warning(f"Failed to register weather domain: {e}")

    try:
        from domains.sentiment.fetcher import SentimentFetcher
        from domains.sentiment.processor import SentimentProcessor
        from domains.sentiment.storage import SentimentStorage

        fetcher = SentimentFetcher(_config.__dict__, _http_client)
        processor = SentimentProcessor()
        storage = SentimentStorage(_db)
        orch = DomainOrchestrator(fetcher, processor, storage, "sentiment_data", "sentiment", _db)
        _orchestrators["sentiment_data"] = orch

        register_domain_job(
            _scheduler, "sentiment_data",
            orch.run, _config.refresh_intervals.news_sentiment,
        )
        logger.info("Sentiment domain registered")
    except Exception as e:
        logger.warning(f"Failed to register sentiment domain: {e}")

    # Run initial fetch for all domains
    for name, orch in _orchestrators.items():
        try:
            await orch.run()
        except Exception as e:
            logger.warning(f"Initial fetch failed for {name}: {e}")


app = FastAPI(
    title="Coal Equity Intelligence Dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

_allowed_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]
# Allow Railway-assigned domain
if os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
    _allowed_origins.append(f"https://{os.environ['RAILWAY_PUBLIC_DOMAIN']}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from routes.overview import router as overview_router
from routes.alerts import router as alerts_router
from routes.upload import router as upload_router
from routes.system import router as system_router

app.include_router(overview_router, prefix="/api", tags=["overview"])
app.include_router(alerts_router, prefix="/api/alerts", tags=["alerts"])
app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(system_router, prefix="/api/system", tags=["system"])

# Domain routers
try:
    from domains.company.routes import router as company_router
    app.include_router(company_router, prefix="/api/company", tags=["company"])
except ImportError:
    pass

try:
    from domains.pricing.routes import router as pricing_router
    app.include_router(pricing_router, prefix="/api/pricing", tags=["pricing"])
except ImportError:
    pass

try:
    from domains.supply.routes import router as supply_router
    app.include_router(supply_router, prefix="/api/supply", tags=["supply"])
except ImportError:
    pass

try:
    from domains.macro.routes import router as macro_router
    app.include_router(macro_router, prefix="/api/macro", tags=["macro"])
except ImportError:
    pass

try:
    from domains.demand.routes import router as demand_router
    app.include_router(demand_router, prefix="/api/demand", tags=["demand"])
except ImportError:
    pass

try:
    from domains.weather.routes import router as weather_router
    app.include_router(weather_router, prefix="/api/weather", tags=["weather"])
except ImportError:
    pass

try:
    from domains.sentiment.routes import router as sentiment_router
    app.include_router(sentiment_router, prefix="/api/sentiment", tags=["sentiment"])
except ImportError:
    pass

try:
    from domains.trade_flows.routes import router as trade_flows_router
    app.include_router(trade_flows_router, prefix="/api/trade-flows", tags=["trade-flows"])
except ImportError:
    pass

# ---------- Static file serving for production (Railway) ----------
# When the React frontend is built, its output goes to /app/static or ../frontend/dist.
# FastAPI serves those files and falls back to index.html for SPA routing.

STATIC_DIR = Path(os.environ.get("STATIC_DIR", "/app/static"))

# Also check relative path for local dev with built frontend
if not STATIC_DIR.exists():
    _alt = Path(__file__).parent.parent / "frontend" / "dist"
    if _alt.exists():
        STATIC_DIR = _alt

if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    # Serve static assets (JS, CSS, images) at /assets
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Serve other static files (favicon, manifest, etc.)
    @app.get("/favicon.svg")
    @app.get("/favicon.ico")
    async def favicon():
        for name in ("favicon.svg", "favicon.ico"):
            fpath = STATIC_DIR / name
            if fpath.exists():
                return FileResponse(str(fpath))
        return FileResponse(str(STATIC_DIR / "index.html"))

    # SPA catch-all: serve index.html for any non-API route
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        # Don't intercept API routes or docs
        if full_path.startswith("api/") or full_path in ("docs", "redoc", "openapi.json"):
            return
        # Try to serve exact file first (e.g. robots.txt)
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        # Otherwise return index.html for client-side routing
        return FileResponse(str(STATIC_DIR / "index.html"))

    logger.info(f"Serving frontend from {STATIC_DIR}")
else:
    logger.info(f"No frontend build found at {STATIC_DIR} — API-only mode")
