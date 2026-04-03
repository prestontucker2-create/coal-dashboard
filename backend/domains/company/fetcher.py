import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from domains.base import BaseFetcher

logger = logging.getLogger(__name__)

DEFAULT_TICKERS = [
    "BTU", "CEIX", "CNXR", "HCC", "AMR", "ARLP",  # US
    "WHC.AX", "TGA.L", "YAL.AX",                    # International
]

# Yahoo Finance chart API — free, no key required
YF_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"


class CompanyFetcher(BaseFetcher):
    """Fetches daily OHLCV stock price data for coal equity tickers via Yahoo Finance API."""

    async def fetch(self, **kwargs) -> dict[str, Any]:
        period = kwargs.get("period", "1y")

        # Build ticker list from watchlist config or fall back to defaults
        watchlist = self.config.get("watchlist", [])
        if watchlist:
            tickers = [item.ticker for item in watchlist]
        else:
            tickers = DEFAULT_TICKERS

        logger.info(f"Fetching stock prices for {len(tickers)} tickers: {tickers}")

        # Fetch all tickers concurrently
        tasks = [self._fetch_ticker(ticker, period) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        records = []
        for ticker, result in zip(tickers, results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching {ticker}: {result}")
                continue
            records.extend(result)

        logger.info(f"Fetched {len(records)} price rows across {len(tickers)} tickers")
        return {"prices": records}

    async def _fetch_ticker(self, ticker: str, period: str) -> list[dict[str, Any]]:
        """Fetch OHLCV data for a single ticker from Yahoo Finance chart API."""
        records: list[dict[str, Any]] = []

        # Map period string to Yahoo Finance range parameter
        range_map = {
            "5d": "5d", "1w": "5d", "1mo": "1mo", "1m": "1mo",
            "3mo": "3mo", "3m": "3mo", "6mo": "6mo", "6m": "6mo",
            "1y": "1y", "2y": "2y", "3y": "5y", "5y": "5y",
        }
        yf_range = range_map.get(period.lower(), "1y")

        params = {
            "range": yf_range,
            "interval": "1d",
            "includeAdjustedClose": "true",
        }

        try:
            url = YF_CHART_URL.format(ticker=ticker)
            http_resp = await self.fetch_with_retry(url, params=params)
            resp = http_resp.json()

            if not resp or "chart" not in resp:
                logger.warning(f"No chart data for {ticker}")
                return records

            result = resp["chart"].get("result", [])
            if not result:
                logger.warning(f"Empty result for {ticker}")
                return records

            data = result[0]
            timestamps = data.get("timestamp", [])
            quote = data.get("indicators", {}).get("quote", [{}])[0]
            adj_close_data = data.get("indicators", {}).get("adjclose", [{}])
            adj_closes = adj_close_data[0].get("adjclose", []) if adj_close_data else []

            opens = quote.get("open", [])
            highs = quote.get("high", [])
            lows = quote.get("low", [])
            closes = quote.get("close", [])
            volumes = quote.get("volume", [])

            for i, ts in enumerate(timestamps):
                close_val = closes[i] if i < len(closes) else None
                if close_val is None:
                    continue

                date_str = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")

                records.append({
                    "ticker": ticker,
                    "date": date_str,
                    "open": float(opens[i] or 0) if i < len(opens) else 0.0,
                    "high": float(highs[i] or 0) if i < len(highs) else 0.0,
                    "low": float(lows[i] or 0) if i < len(lows) else 0.0,
                    "close": float(close_val),
                    "volume": int(volumes[i] or 0) if i < len(volumes) else 0,
                    "adj_close": float(adj_closes[i]) if i < len(adj_closes) and adj_closes[i] else float(close_val),
                })

        except Exception as e:
            logger.error(f"Error fetching {ticker}: {e}")

        return records
