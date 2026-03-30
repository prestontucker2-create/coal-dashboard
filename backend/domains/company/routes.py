import logging
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import text

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/prices")
async def get_prices(
    tickers: Optional[str] = Query(None, description="Comma-separated ticker symbols"),
    timeframe: str = Query("3M", description="Timeframe: 1W, 1M, 3M, 6M, 1Y, 3Y, ALL"),
):
    """Return historical stock prices, optionally filtered by tickers and timeframe."""
    from main import _db

    storage = _get_storage(_db)
    filters: dict = {}
    if tickers:
        filters["tickers"] = [t.strip().upper() for t in tickers.split(",")]

    rows = await storage.query(filters, timeframe=timeframe)
    return {"prices": rows, "count": len(rows)}


@router.get("/latest")
async def get_latest_prices():
    """Return the most recent price row for every ticker in the watchlist."""
    from main import _db

    async with _db.session_factory() as session:
        result = await session.execute(text("""
            SELECT s1.ticker, s1.date, s1.open, s1.high, s1.low, s1.close,
                   s1.volume, s1.adj_close,
                   s2.close AS prev_close
            FROM stock_prices s1
            LEFT JOIN stock_prices s2
                ON s1.ticker = s2.ticker
                AND s2.date = (
                    SELECT MAX(date) FROM stock_prices
                    WHERE ticker = s1.ticker AND date < s1.date
                )
            WHERE s1.date = (
                SELECT MAX(date) FROM stock_prices WHERE ticker = s1.ticker
            )
            ORDER BY s1.ticker
        """))
        rows = result.fetchall()

    prices = []
    for r in rows:
        close = r[5]
        prev_close = r[8] if r[8] is not None else close
        change_pct = ((close - prev_close) / prev_close * 100) if prev_close else 0.0

        prices.append({
            "ticker": r[0],
            "date": r[1],
            "open": r[2],
            "high": r[3],
            "low": r[4],
            "close": close,
            "volume": r[6],
            "adj_close": r[7],
            "prev_close": prev_close,
            "change_pct": round(change_pct, 2),
        })

    return {"prices": prices}


@router.get("/peer-comparison")
async def get_peer_comparison(
    tickers: Optional[str] = Query(None, description="Comma-separated ticker symbols"),
):
    """
    Side-by-side comparison of the latest financials for each requested ticker.
    Falls back to the full watchlist if no tickers are specified.
    """
    from main import _db

    async with _db.session_factory() as session:
        # Determine which tickers to compare
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(",")]
        else:
            # Use all tickers that have data
            result = await session.execute(
                text("SELECT DISTINCT ticker FROM stock_prices ORDER BY ticker")
            )
            ticker_list = [r[0] for r in result.fetchall()]

        if not ticker_list:
            return {"peers": []}

        # Latest price for each ticker
        placeholders = ", ".join(f":t{i}" for i in range(len(ticker_list)))
        params = {f"t{i}": t for i, t in enumerate(ticker_list)}

        result = await session.execute(
            text(f"""
                SELECT s.ticker, s.close, s.volume, s.date, s.adj_close
                FROM stock_prices s
                INNER JOIN (
                    SELECT ticker, MAX(date) AS max_date
                    FROM stock_prices
                    WHERE ticker IN ({placeholders})
                    GROUP BY ticker
                ) latest ON s.ticker = latest.ticker AND s.date = latest.max_date
                ORDER BY s.ticker
            """),
            params,
        )
        price_rows = result.fetchall()

        # Latest company financials for each ticker (if available)
        result = await session.execute(
            text(f"""
                SELECT cf.ticker, cf.metric, cf.value, cf.period
                FROM company_financials cf
                INNER JOIN (
                    SELECT ticker, metric, MAX(period) AS max_period
                    FROM company_financials
                    WHERE ticker IN ({placeholders})
                    GROUP BY ticker, metric
                ) latest ON cf.ticker = latest.ticker
                       AND cf.metric = latest.metric
                       AND cf.period = latest.max_period
                ORDER BY cf.ticker, cf.metric
            """),
            params,
        )
        fin_rows = result.fetchall()

        # Group financials by ticker
        financials_map: dict[str, dict[str, float]] = {}
        for r in fin_rows:
            ticker = r[0]
            if ticker not in financials_map:
                financials_map[ticker] = {}
            financials_map[ticker][r[1]] = r[2]

        peers = []
        for r in price_rows:
            ticker = r[0]
            peers.append({
                "ticker": ticker,
                "latest_close": r[1],
                "volume": r[2],
                "date": r[3],
                "adj_close": r[4],
                "financials": financials_map.get(ticker, {}),
            })

    return {"peers": peers}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_storage(db):
    """Construct a CompanyStorage instance from the global DatabaseManager."""
    from domains.company.storage import CompanyStorage
    return CompanyStorage(db)
