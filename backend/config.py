import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WatchlistItem:
    ticker: str
    name: str
    exchange: str
    type: str = "thermal"
    primary: bool = False


@dataclass
class ApiKeys:
    eia: str = ""
    fred: str = ""
    oilprice: str = ""
    newsapi: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "coal-dashboard/1.0"
    entsoe: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


@dataclass
class RefreshIntervals:
    stock_prices_intraday: int = 300
    stock_prices_daily: int = 86400
    coal_benchmarks: int = 720
    eia_weekly: int = 86400
    fred_macro: int = 3600
    news_sentiment: int = 1800
    sec_filings: int = 86400
    weather: int = 21600
    entsoe: int = 3600
    cftc_cot: int = 86400
    company_financials: int = 86400


@dataclass
class AlertChannels:
    telegram: bool = True
    email: bool = False


@dataclass
class EmailConfig:
    smtp_host: str = ""
    smtp_port: int = 587
    sender: str = ""
    recipient: str = ""


@dataclass
class AlertConfig:
    enabled: bool = True
    cooldown_minutes: int = 60
    channels: AlertChannels = field(default_factory=AlertChannels)
    email: EmailConfig = field(default_factory=EmailConfig)


@dataclass
class DatabaseConfig:
    path: str = "./data/coal_dashboard.db"


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    frontend_url: str = "http://localhost:5173"


@dataclass
class AppConfig:
    api_keys: ApiKeys = field(default_factory=ApiKeys)
    watchlist: list[WatchlistItem] = field(default_factory=list)
    refresh_intervals: RefreshIntervals = field(default_factory=RefreshIntervals)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    @property
    def tickers(self) -> list[str]:
        return [w.ticker for w in self.watchlist]

    @property
    def primary_tickers(self) -> list[str]:
        return [w.ticker for w in self.watchlist if w.primary]


# Default watchlist used when no config.yaml is present (Railway / cloud deploys)
DEFAULT_WATCHLIST = [
    {"ticker": "BTU", "name": "Peabody Energy", "exchange": "NYSE", "type": "thermal", "primary": True},
    {"ticker": "WHC.AX", "name": "Whitehaven Coal", "exchange": "ASX", "type": "thermal_met", "primary": True},
    {"ticker": "CEIX", "name": "CONSOL Energy", "exchange": "NYSE", "type": "thermal", "primary": False},
    {"ticker": "CNXR", "name": "Arch Resources", "exchange": "NYSE", "type": "met", "primary": False},
    {"ticker": "HCC", "name": "Warrior Met Coal", "exchange": "NYSE", "type": "met", "primary": False},
    {"ticker": "AMR", "name": "Alpha Metallurgical", "exchange": "NYSE", "type": "met", "primary": False},
    {"ticker": "ARLP", "name": "Alliance Resource Partners", "exchange": "NASDAQ", "type": "thermal", "primary": False},
    {"ticker": "TGA.L", "name": "Thungela Resources", "exchange": "LSE", "type": "thermal", "primary": False},
    {"ticker": "YAL.AX", "name": "Yancoal Australia", "exchange": "ASX", "type": "thermal_met", "primary": False},
]


def _load_from_env() -> AppConfig:
    """Build AppConfig from environment variables (for Railway / cloud deploys)."""
    api_keys = ApiKeys(
        eia=os.environ.get("EIA_API_KEY", ""),
        fred=os.environ.get("FRED_API_KEY", ""),
        oilprice=os.environ.get("OILPRICE_API_KEY", ""),
        newsapi=os.environ.get("NEWSAPI_KEY", ""),
        reddit_client_id=os.environ.get("REDDIT_CLIENT_ID", ""),
        reddit_client_secret=os.environ.get("REDDIT_CLIENT_SECRET", ""),
        reddit_user_agent=os.environ.get("REDDIT_USER_AGENT", "coal-dashboard/1.0"),
        entsoe=os.environ.get("ENTSOE_API_KEY", ""),
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
    )

    watchlist = [WatchlistItem(**item) for item in DEFAULT_WATCHLIST]

    db_path = os.environ.get("DATABASE_PATH", "/data/coal_dashboard.db")
    port = int(os.environ.get("PORT", "8000"))

    return AppConfig(
        api_keys=api_keys,
        watchlist=watchlist,
        refresh_intervals=RefreshIntervals(),
        alerts=AlertConfig(
            enabled=os.environ.get("ALERTS_ENABLED", "true").lower() == "true",
            channels=AlertChannels(
                telegram=bool(os.environ.get("TELEGRAM_BOT_TOKEN", "")),
            ),
        ),
        database=DatabaseConfig(path=db_path),
        server=ServerConfig(host="0.0.0.0", port=port),
    )


def load_config(path: Optional[str] = None) -> AppConfig:
    # If RAILWAY_ENVIRONMENT is set, or USE_ENV_CONFIG is truthy, load from env vars
    if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("USE_ENV_CONFIG", "").lower() in ("1", "true", "yes"):
        print("Loading config from environment variables (Railway mode)")
        config = _load_from_env()
    else:
        if path is None:
            path = os.environ.get("CONFIG_PATH", "config.yaml")

        config_path = Path(path)
        if not config_path.exists():
            print(f"Warning: config file {path} not found, trying environment variables")
            config = _load_from_env()
        else:
            with open(config_path) as f:
                raw = yaml.safe_load(f) or {}

            api_keys = ApiKeys(**raw.get("api_keys", {}))

            watchlist = []
            for item in raw.get("watchlist", []):
                watchlist.append(WatchlistItem(**item))

            ri_data = raw.get("refresh_intervals", {})
            refresh_intervals = RefreshIntervals(**ri_data)

            alert_raw = raw.get("alerts", {})
            channels = AlertChannels(**alert_raw.get("channels", {}))
            email = EmailConfig(**alert_raw.get("email", {}))
            alert_config = AlertConfig(
                enabled=alert_raw.get("enabled", True),
                cooldown_minutes=alert_raw.get("cooldown_minutes", 60),
                channels=channels,
                email=email,
            )

            db = DatabaseConfig(**raw.get("database", {}))
            server = ServerConfig(**raw.get("server", {}))

            config = AppConfig(
                api_keys=api_keys,
                watchlist=watchlist,
                refresh_intervals=refresh_intervals,
                alerts=alert_config,
                database=db,
                server=server,
            )

    # Allow env var overrides even when loading from yaml
    # This lets Railway secrets override a checked-in config
    if os.environ.get("EIA_API_KEY"):
        config.api_keys.eia = os.environ["EIA_API_KEY"]
    if os.environ.get("FRED_API_KEY"):
        config.api_keys.fred = os.environ["FRED_API_KEY"]
    if os.environ.get("OILPRICE_API_KEY"):
        config.api_keys.oilprice = os.environ["OILPRICE_API_KEY"]
    if os.environ.get("NEWSAPI_KEY"):
        config.api_keys.newsapi = os.environ["NEWSAPI_KEY"]
    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        config.api_keys.telegram_bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    if os.environ.get("TELEGRAM_CHAT_ID"):
        config.api_keys.telegram_chat_id = os.environ["TELEGRAM_CHAT_ID"]
    if os.environ.get("PORT"):
        config.server.port = int(os.environ["PORT"])
    if os.environ.get("DATABASE_PATH"):
        config.database.path = os.environ["DATABASE_PATH"]

    missing_keys = []
    for key_name in ["eia", "fred"]:
        if not getattr(config.api_keys, key_name):
            missing_keys.append(key_name)
    if missing_keys:
        print(f"Warning: Missing API keys: {', '.join(missing_keys)}. Some data sources will be unavailable.")

    return config
