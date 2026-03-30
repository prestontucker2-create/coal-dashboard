-- PRICING DOMAIN
CREATE TABLE IF NOT EXISTS coal_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    benchmark TEXT NOT NULL,
    price_usd REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    timestamp DATETIME NOT NULL,
    source TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(benchmark, timestamp)
);

CREATE TABLE IF NOT EXISTS gas_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    benchmark TEXT NOT NULL,
    price REAL NOT NULL,
    unit TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    source TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(benchmark, timestamp)
);

CREATE TABLE IF NOT EXISTS price_spreads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spread_name TEXT NOT NULL,
    value REAL NOT NULL,
    timestamp DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(spread_name, timestamp)
);

-- SUPPLY DOMAIN
CREATE TABLE IF NOT EXISTS us_coal_production (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region TEXT NOT NULL,
    production_tons REAL NOT NULL,
    period_type TEXT NOT NULL,
    period_date DATE NOT NULL,
    source TEXT DEFAULT 'eia',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(region, period_type, period_date)
);

CREATE TABLE IF NOT EXISTS coal_inventories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location TEXT NOT NULL,
    inventory_tons REAL NOT NULL,
    days_supply REAL,
    period_date DATE NOT NULL,
    source TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(location, period_date)
);

CREATE TABLE IF NOT EXISTS international_supply (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    period_date DATE NOT NULL,
    source TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(country, metric, period_date)
);

-- DEMAND DOMAIN
CREATE TABLE IF NOT EXISTS power_generation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region TEXT NOT NULL,
    fuel_type TEXT NOT NULL,
    generation_mwh REAL NOT NULL,
    period_type TEXT NOT NULL,
    period_date DATE NOT NULL,
    source TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(region, fuel_type, period_type, period_date)
);

CREATE TABLE IF NOT EXISTS steel_production (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region TEXT NOT NULL,
    production_mt REAL NOT NULL,
    period_date DATE NOT NULL,
    source TEXT DEFAULT 'worldsteel',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(region, period_date)
);

-- TRADE FLOWS DOMAIN
CREATE TABLE IF NOT EXISTS trade_flows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exporter TEXT NOT NULL,
    importer TEXT NOT NULL,
    coal_type TEXT NOT NULL,
    volume_mt REAL NOT NULL,
    value_usd REAL,
    period_date DATE NOT NULL,
    source TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exporter, importer, coal_type, period_date)
);

-- MACRO DOMAIN
CREATE TABLE IF NOT EXISTS macro_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator TEXT NOT NULL,
    value REAL NOT NULL,
    timestamp DATETIME NOT NULL,
    source TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(indicator, timestamp)
);

CREATE TABLE IF NOT EXISTS cot_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract TEXT NOT NULL,
    long_positions INTEGER,
    short_positions INTEGER,
    net_position INTEGER,
    change_week INTEGER,
    report_date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(contract, report_date)
);

-- COMPANY DOMAIN
CREATE TABLE IF NOT EXISTS stock_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    adj_close REAL,
    date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, date)
);

CREATE TABLE IF NOT EXISTS company_financials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL,
    period TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, metric, period)
);

CREATE TABLE IF NOT EXISTS insider_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    insider_name TEXT NOT NULL,
    title TEXT,
    transaction_type TEXT NOT NULL,
    shares INTEGER NOT NULL,
    price REAL,
    total_value REAL,
    transaction_date DATE NOT NULL,
    filing_date DATE NOT NULL,
    source TEXT DEFAULT 'sec_edgar',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, insider_name, transaction_type, transaction_date, shares)
);

CREATE TABLE IF NOT EXISTS institutional_ownership (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    institution TEXT NOT NULL,
    shares INTEGER NOT NULL,
    value_usd REAL,
    pct_portfolio REAL,
    change_shares INTEGER,
    filing_date DATE NOT NULL,
    source TEXT DEFAULT 'sec_13f',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, institution, filing_date)
);

CREATE TABLE IF NOT EXISTS analyst_estimates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    metric TEXT NOT NULL,
    period TEXT NOT NULL,
    consensus REAL,
    high REAL,
    low REAL,
    num_analysts INTEGER,
    retrieved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, metric, period)
);

CREATE TABLE IF NOT EXISTS short_interest (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    short_shares INTEGER,
    short_pct_float REAL,
    days_to_cover REAL,
    settlement_date DATE NOT NULL,
    source TEXT DEFAULT 'nasdaq',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, settlement_date)
);

-- WEATHER DOMAIN
CREATE TABLE IF NOT EXISTS degree_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region TEXT NOT NULL,
    hdd REAL,
    cdd REAL,
    deviation_from_normal REAL,
    period_date DATE NOT NULL,
    source TEXT DEFAULT 'noaa',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(region, period_date)
);

CREATE TABLE IF NOT EXISTS enso_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    oni_value REAL NOT NULL,
    phase TEXT NOT NULL,
    period_date DATE NOT NULL,
    source TEXT DEFAULT 'noaa',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(period_date)
);

CREATE TABLE IF NOT EXISTS rainfall_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region TEXT NOT NULL,
    rainfall_mm REAL NOT NULL,
    anomaly_pct REAL,
    period_date DATE NOT NULL,
    source TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(region, period_date)
);

-- SENTIMENT DOMAIN
CREATE TABLE IF NOT EXISTS news_headlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT,
    source_name TEXT,
    published_at DATETIME,
    sentiment_score REAL,
    relevance_tag TEXT,
    tickers_mentioned TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reddit_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subreddit TEXT NOT NULL,
    post_title TEXT NOT NULL,
    post_url TEXT,
    score INTEGER,
    num_comments INTEGER,
    tickers_mentioned TEXT,
    sentiment_score REAL,
    posted_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ALERTS & SIGNALS
CREATE TABLE IF NOT EXISTS alert_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    domain TEXT NOT NULL,
    metric TEXT NOT NULL,
    condition TEXT NOT NULL,
    threshold REAL NOT NULL,
    timeframe_minutes INTEGER DEFAULT 1440,
    is_active INTEGER DEFAULT 1,
    channels TEXT DEFAULT 'telegram',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_config_id INTEGER REFERENCES alert_configs(id),
    triggered_value REAL NOT NULL,
    message TEXT NOT NULL,
    dispatched_via TEXT,
    triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS signal_board (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_name TEXT NOT NULL,
    direction TEXT NOT NULL,
    strength REAL NOT NULL,
    reasoning TEXT,
    domain TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(signal_name)
);

-- DATA FRESHNESS
CREATE TABLE IF NOT EXISTS data_freshness (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    last_success DATETIME,
    last_attempt DATETIME,
    last_error TEXT,
    expected_interval_seconds INTEGER,
    record_count INTEGER DEFAULT 0
);

-- CSV UPLOADS (for Tier 3 premium data)
CREATE TABLE IF NOT EXISTS csv_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_type TEXT NOT NULL,
    filename TEXT NOT NULL,
    rows_inserted INTEGER DEFAULT 0,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
