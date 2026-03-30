import logging
import math
from typing import Any

from domains.base import BaseProcessor

logger = logging.getLogger(__name__)


class CompanyProcessor(BaseProcessor):
    """Cleans and normalises raw stock price data from the CompanyFetcher."""

    def process(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        prices = raw_data.get("prices", [])
        cleaned: list[dict[str, Any]] = []

        for row in prices:
            # Skip rows where the close price is missing or NaN
            close = row.get("close")
            if close is None or (isinstance(close, float) and math.isnan(close)):
                continue

            # Ensure date is an ISO-format string (YYYY-MM-DD)
            date_val = row.get("date", "")
            if hasattr(date_val, "isoformat"):
                date_str = date_val.isoformat()
            else:
                date_str = str(date_val)

            cleaned.append({
                "ticker": row["ticker"],
                "date": date_str,
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": close,
                "volume": row.get("volume"),
                "adj_close": row.get("adj_close", close),
            })

        logger.info(
            f"Processed {len(cleaned)} stock price records "
            f"(dropped {len(prices) - len(cleaned)} rows with NaN close)"
        )
        return cleaned
