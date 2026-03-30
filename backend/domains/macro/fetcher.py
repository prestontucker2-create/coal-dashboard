import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from domains.base import BaseFetcher

logger = logging.getLogger(__name__)

# FRED series mapping: series_id -> human-readable label
FRED_SERIES = {
    "DEXUSAL": "AUD/USD Exchange Rate",
    "DTWEXBGS": "Trade Weighted Dollar Index",
    "DGS10": "10-Year Treasury Yield",
    "DHHNGSP": "Henry Hub Natural Gas Spot",
    "NAPMPI": "ISM Manufacturing PMI",
}

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


class MacroFetcher(BaseFetcher):
    """Fetches macro-economic indicators from the FRED API.

    Key series:
    - DEXUSAL:  AUD/USD exchange rate (critical for WHC.AX margin analysis).
                FRED reports USD per 1 AUD, so 0.65 means 1 AUD = 0.65 USD.
    - DTWEXBGS: Trade Weighted Dollar Index (DXY proxy)
    - DGS10:    10-Year US Treasury Yield
    - DHHNGSP:  Henry Hub Natural Gas daily spot price
    - NAPMPI:   ISM Manufacturing PMI
    """

    async def fetch(self, **kwargs) -> dict[str, Any]:
        api_keys = self.config.get("api_keys")
        if api_keys is None:
            logger.warning("No api_keys in config -- skipping FRED fetch")
            return {}

        fred_key = getattr(api_keys, "fred", "") if hasattr(api_keys, "fred") else ""
        if not fred_key:
            logger.warning("FRED API key is missing -- skipping macro fetch")
            return {}

        observation_start = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
        all_indicators: list[dict[str, Any]] = []

        for series_id, label in FRED_SERIES.items():
            try:
                params = {
                    "series_id": series_id,
                    "api_key": fred_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 500,
                    "observation_start": observation_start,
                }
                resp = await self.fetch_with_retry(FRED_BASE_URL, params=params)
                data = resp.json()

                observations = data.get("observations", [])
                logger.info(f"FRED {series_id}: fetched {len(observations)} observations")

                for obs in observations:
                    all_indicators.append({
                        "indicator": series_id,
                        "value": obs.get("value"),
                        "timestamp": obs.get("date"),
                        "source": "fred",
                    })

            except Exception as e:
                logger.error(f"Error fetching FRED series {series_id}: {e}")
                continue

        logger.info(f"FRED fetch complete: {len(all_indicators)} total observations across {len(FRED_SERIES)} series")
        return {"indicators": all_indicators}
