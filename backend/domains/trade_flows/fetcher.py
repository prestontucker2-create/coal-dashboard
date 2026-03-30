"""
Trade flows domain fetcher.

Pulls US coal export data from the EIA API v2 to track international
coal trade patterns and export volumes.
"""

from __future__ import annotations

import logging
from typing import Any

from domains.base import BaseFetcher

logger = logging.getLogger(__name__)

# EIA v2 endpoint for coal exports
EXPORTS_URL = "https://api.eia.gov/v2/coal/exports/data/"


class TradeFlowFetcher(BaseFetcher):
    """Fetch US coal trade flow data from the EIA API."""

    # ------------------------------------------------------------------ #
    #  Main entry point
    # ------------------------------------------------------------------ #
    async def fetch(self, **kwargs) -> dict[str, Any]:
        api_key = self._get_api_key()
        if not api_key:
            logger.warning(
                "EIA API key not configured -- skipping trade flow fetch"
            )
            return {"trade_flows": []}

        trade_flows = await self._fetch_exports(api_key)

        logger.info(
            "TradeFlowFetcher complete: %d export records",
            len(trade_flows),
        )
        return {"trade_flows": trade_flows}

    # ------------------------------------------------------------------ #
    #  EIA coal exports fetch
    # ------------------------------------------------------------------ #
    async def _fetch_exports(self, api_key: str) -> list[dict]:
        """Pull quarterly US coal export data from EIA v2."""
        params = {
            "api_key": api_key,
            "frequency": "quarterly",
            "data[0]": "quantity",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 100,
        }

        try:
            resp = await self.fetch_with_retry(EXPORTS_URL, params=params)
            payload = resp.json()

            data = payload.get("response", {}).get("data")
            if data is None:
                data = payload.get("data")

            if not isinstance(data, list):
                logger.warning(
                    "EIA exports response missing 'response.data' array -- "
                    "payload keys: %s",
                    list(payload.keys()),
                )
                return []

            logger.info("EIA coal exports: retrieved %d rows", len(data))
            return data

        except Exception as exc:
            logger.error("EIA coal exports fetch failed: %s", exc)
            return []

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    def _get_api_key(self) -> str:
        """Return the EIA key from config, or empty string if missing."""
        api_keys = self.config.get("api_keys")
        if api_keys is None:
            return ""
        if hasattr(api_keys, "eia"):
            return api_keys.eia or ""
        if isinstance(api_keys, dict):
            return api_keys.get("eia", "")
        return ""
