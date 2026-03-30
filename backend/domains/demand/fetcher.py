"""
Demand domain fetcher.

Pulls US electricity generation data by fuel type from the EIA API v2,
enabling analysis of coal's share in the power generation mix versus
natural gas, nuclear, solar, and wind.
"""

from __future__ import annotations

import logging
from typing import Any

from domains.base import BaseFetcher

logger = logging.getLogger(__name__)

# EIA v2 endpoint for electric power operational data
GENERATION_URL = (
    "https://api.eia.gov/v2/electricity/electric-power-operational-data/data/"
)


class DemandFetcher(BaseFetcher):
    """Fetch US electricity generation by fuel type from the EIA API."""

    # ------------------------------------------------------------------ #
    #  Main entry point
    # ------------------------------------------------------------------ #
    async def fetch(self, **kwargs) -> dict[str, Any]:
        api_key = self._get_api_key()
        if not api_key:
            logger.warning(
                "EIA API key not configured -- skipping demand/generation fetch"
            )
            return {"generation": []}

        generation = await self._fetch_generation(api_key)

        logger.info(
            "DemandFetcher complete: %d generation records",
            len(generation),
        )
        return {"generation": generation}

    # ------------------------------------------------------------------ #
    #  EIA generation fetch
    # ------------------------------------------------------------------ #
    async def _fetch_generation(self, api_key: str) -> list[dict]:
        """Pull monthly generation data by fuel type from EIA v2.

        Fuel type facets requested:
            COL  - Coal
            NG   - Natural Gas
            NUC  - Nuclear
            SUN  - Solar
            WND  - Wind
            ALL  - All fuels total
        Sector 99 = all sectors (electric power industry total).
        """
        params = {
            "api_key": api_key,
            "frequency": "monthly",
            "data[0]": "generation",
            "facets[fueltypeid][]": ["COL", "NG", "NUC", "SUN", "WND", "ALL"],
            "facets[sectorid][]": "99",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 200,
        }

        try:
            resp = await self.fetch_with_retry(GENERATION_URL, params=params)
            payload = resp.json()

            data = payload.get("response", {}).get("data")
            if data is None:
                data = payload.get("data")

            if not isinstance(data, list):
                logger.warning(
                    "EIA generation response missing 'response.data' array -- "
                    "payload keys: %s",
                    list(payload.keys()),
                )
                return []

            logger.info("EIA generation: retrieved %d rows", len(data))
            return data

        except Exception as exc:
            logger.error("EIA generation fetch failed: %s", exc)
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
