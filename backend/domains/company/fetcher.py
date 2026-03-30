import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import yfinance as yf

from domains.base import BaseFetcher

logger = logging.getLogger(__name__)

DEFAULT_TICKERS = [
    "BTU", "CEIX", "CNXR", "HCC", "AMR", "ARLP",  # US
    "WHC.AX", "TGA.L", "YAL.AX",                    # International
]


class CompanyFetcher(BaseFetcher):
    """Fetches daily OHLCV stock price data for coal equity tickers via yfinance."""

    async def fetch(self, **kwargs) -> dict[str, Any]:
        period = kwargs.get("period", "1y")

        # Build ticker list from watchlist config or fall back to defaults
        watchlist = self.config.get("watchlist", [])
        if watchlist:
            tickers = [item.ticker for item in watchlist]
        else:
            tickers = DEFAULT_TICKERS

        logger.info(f"Fetching stock prices for {len(tickers)} tickers: {tickers}")

        # yfinance.download() is synchronous -- run in a thread so we
        # don't block the async event loop.
        records = await asyncio.to_thread(self._download_prices, tickers, period)

        logger.info(f"Fetched {len(records)} price rows across {len(tickers)} tickers")
        return {"prices": records}

    # ------------------------------------------------------------------
    # Synchronous helper executed inside a thread
    # ------------------------------------------------------------------
    @staticmethod
    def _download_prices(tickers: list[str], period: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []

        try:
            df = yf.download(
                tickers=tickers,
                period=period,
                interval="1d",
                group_by="ticker",
                auto_adjust=False,
                threads=True,
            )
        except Exception as e:
            logger.error(f"yfinance batch download failed: {e}")
            return records

        if df is None or df.empty:
            logger.warning("yfinance returned empty dataframe")
            return records

        # When only one ticker is requested yfinance returns a simple
        # (non-multi-level) column index.  Normalise to the multi-ticker
        # layout so the parsing loop below works uniformly.
        if len(tickers) == 1:
            df.columns = pd.MultiIndex.from_product([tickers, df.columns])

        for ticker in tickers:
            try:
                if ticker not in df.columns.get_level_values(0):
                    logger.warning(f"Ticker {ticker} not found in download results")
                    continue

                ticker_df = df[ticker].copy()

                # Drop rows where the close price is missing (the ticker
                # may not have traded on that date).
                ticker_df = ticker_df.dropna(subset=["Close"])

                for idx, row in ticker_df.iterrows():
                    date_val = idx
                    if isinstance(date_val, pd.Timestamp):
                        date_str = date_val.strftime("%Y-%m-%d")
                    else:
                        date_str = str(date_val)

                    records.append({
                        "ticker": ticker,
                        "date": date_str,
                        "open": float(row.get("Open", 0) or 0),
                        "high": float(row.get("High", 0) or 0),
                        "low": float(row.get("Low", 0) or 0),
                        "close": float(row["Close"]),
                        "volume": int(row.get("Volume", 0) or 0),
                        "adj_close": float(row.get("Adj Close", row["Close"]) or row["Close"]),
                    })
            except Exception as e:
                logger.error(f"Error processing ticker {ticker}: {e}")
                continue

        return records
