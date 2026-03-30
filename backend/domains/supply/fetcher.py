"""
Supply domain fetcher -- pulls US coal production and inventory data from EIA API v2.
"""

from typing import Any
import logging

from domains.base import BaseFetcher

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# EIA API v2 endpoints
# ---------------------------------------------------------------------------
PRODUCTION_URL = "https://api.eia.gov/v2/coal/mine-production/data/"
INVENTORY_URL = (
    "https://api.eia.gov/v2/electricity/electric-power-operational-data/data/"
)


class SupplyFetcher(BaseFetcher):
    """Fetch US coal production and electric-power-sector inventory data."""

    # ----- public interface (required by BaseFetcher) ----------------------

    async def fetch(self, **kwargs) -> dict[str, Any]:
        api_key = self._get_api_key()
        if not api_key:
            logger.warning(
                "EIA API key not configured -- skipping supply fetch"
            )
            return {"production": [], "inventories": []}

        production = await self._fetch_production(api_key)
        inventories = await self._fetch_inventories(api_key)

        logger.info(
            "Supply fetch complete: %d production rows, %d inventory rows",
            len(production),
            len(inventories),
        )
        return {"production": production, "inventories": inventories}

    # ----- internal helpers ------------------------------------------------

    def _get_api_key(self) -> str:
        """Return the EIA key from config, or empty string if missing."""
        api_keys = self.config.get("api_keys")
        if api_keys is None:
            return ""
        # api_keys may be an ApiKeys dataclass or a plain dict
        if hasattr(api_keys, "eia"):
            return api_keys.eia or ""
        if isinstance(api_keys, dict):
            return api_keys.get("eia", "")
        return ""

    async def _fetch_production(self, api_key: str) -> list[dict]:
        """Pull annual/quarterly mine-production data from EIA v2."""
        params = {
            "api_key": api_key,
            "frequency": "annual",
            "data[0]": "production",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 200,
        }
        return await self._eia_get(PRODUCTION_URL, params, label="production")

    async def _fetch_inventories(self, api_key: str) -> list[dict]:
        """Pull monthly coal-stocks data from the electric-power endpoint."""
        params = {
            "api_key": api_key,
            "frequency": "monthly",
            "data[0]": "coal-stocks",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 100,
        }
        return await self._eia_get(INVENTORY_URL, params, label="inventories")

    async def _eia_get(
        self, url: str, params: dict, label: str
    ) -> list[dict]:
        """
        Issue a GET to an EIA v2 endpoint and return the ``response.data``
        array.  Returns an empty list on any error.
        """
        try:
            resp = await self.fetch_with_retry(url, params=params)
            payload = resp.json()

            # EIA v2 nests the actual rows under response -> data
            data = payload.get("response", {}).get("data")
            if data is None:
                # Some endpoints put rows directly under "data"
                data = payload.get("data")

            if not isinstance(data, list):
                logger.warning(
                    "EIA %s response missing 'response.data' array -- "
                    "payload keys: %s",
                    label,
                    list(payload.keys()),
                )
                return []

            return data

        except Exception as exc:
            logger.error("EIA %s fetch failed: %s", label, exc)
            return []
