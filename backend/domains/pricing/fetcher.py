"""
Pricing domain fetcher.

Aggregates coal benchmark prices and natural gas prices from multiple sources:
- OilPriceAPI (Newcastle coal)
- FRED (Henry Hub natural gas)
- EIA (US coal shipment receipts)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from domains.base import BaseFetcher

logger = logging.getLogger(__name__)


class PricingFetcher(BaseFetcher):
    """Fetch coal and gas benchmark prices from public APIs."""

    # ------------------------------------------------------------------ #
    #  Main entry point
    # ------------------------------------------------------------------ #
    async def fetch(self, **kwargs) -> dict[str, Any]:
        coal_prices: list[dict] = []
        gas_prices: list[dict] = []

        # Resolve API keys from config.  _config.__dict__ is passed, so
        # api_keys is the ApiKeys dataclass instance.
        api_keys = self.config.get("api_keys")

        # --- OilPriceAPI (Newcastle coal) ---
        oilprice_key = getattr(api_keys, "oilprice", "") if api_keys else ""
        if oilprice_key:
            newcastle = await self._fetch_oilprice_coal(oilprice_key)
            coal_prices.extend(newcastle)
        else:
            logger.info("No OilPriceAPI key configured -- skipping Newcastle coal fetch")

        # --- EIA (US coal shipment receipt prices) ---
        eia_key = getattr(api_keys, "eia", "") if api_keys else ""
        if eia_key:
            eia_coal = await self._fetch_eia_coal(eia_key)
            coal_prices.extend(eia_coal)
        else:
            logger.info("No EIA key configured -- skipping US coal price fetch")

        # --- FRED (Henry Hub natural gas) ---
        fred_key = getattr(api_keys, "fred", "") if api_keys else ""
        if fred_key:
            hh = await self._fetch_fred_henry_hub(fred_key)
            gas_prices.extend(hh)
        else:
            logger.info("No FRED key configured -- skipping Henry Hub fetch")

        # If we got absolutely nothing for coal, insert a placeholder so
        # downstream processing does not crash.
        if not coal_prices:
            logger.warning(
                "No coal price data retrieved from any source. "
                "Inserting placeholder record."
            )
            coal_prices.append({
                "benchmark": "newcastle",
                "price_usd": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "placeholder",
            })

        logger.info(
            "PricingFetcher complete: %d coal records, %d gas records",
            len(coal_prices),
            len(gas_prices),
        )
        return {"coal_prices": coal_prices, "gas_prices": gas_prices}

    # ------------------------------------------------------------------ #
    #  OilPriceAPI helpers
    # ------------------------------------------------------------------ #
    async def _fetch_oilprice_coal(self, api_key: str) -> list[dict]:
        """Try fetching Newcastle coal from OilPriceAPI.

        The API may not expose a coal-specific code, so we attempt
        COAL_NEWCASTLE_USD first, then fall back to BRENT_CRUDE_USD as a
        proxy (with appropriate logging).
        """
        records: list[dict] = []
        headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}

        # Attempt 1: dedicated coal endpoint
        try:
            resp = await self.fetch_with_retry(
                "https://api.oilpriceapi.com/v1/prices/latest",
                params={"by_code": "COAL_NEWCASTLE_USD"},
                headers=headers,
            )
            data = resp.json()
            price_info = data.get("data", {})
            if price_info and price_info.get("price"):
                records.append({
                    "benchmark": "newcastle",
                    "price_usd": float(price_info["price"]),
                    "timestamp": price_info.get("created_at", datetime.now(timezone.utc).isoformat()),
                    "source": "oilpriceapi",
                })
                logger.info("Newcastle coal price from OilPriceAPI: $%.2f", price_info["price"])
                return records
        except Exception as exc:
            logger.warning("OilPriceAPI coal endpoint unavailable: %s", exc)

        # Attempt 2: Brent crude as energy-sector proxy (logged clearly)
        try:
            resp = await self.fetch_with_retry(
                "https://api.oilpriceapi.com/v1/prices/latest",
                params={"by_code": "BRENT_CRUDE_USD"},
                headers=headers,
            )
            data = resp.json()
            price_info = data.get("data", {})
            if price_info and price_info.get("price"):
                records.append({
                    "benchmark": "brent_crude",
                    "price_usd": float(price_info["price"]),
                    "timestamp": price_info.get("created_at", datetime.now(timezone.utc).isoformat()),
                    "source": "oilpriceapi",
                })
                logger.info(
                    "No direct coal price from OilPriceAPI; stored Brent crude ($%.2f) as energy reference",
                    price_info["price"],
                )
        except Exception as exc:
            logger.warning("OilPriceAPI Brent fallback also failed: %s", exc)

        return records

    # ------------------------------------------------------------------ #
    #  EIA helpers
    # ------------------------------------------------------------------ #
    async def _fetch_eia_coal(self, api_key: str) -> list[dict]:
        """Fetch US coal price data from EIA v2 API (shipment receipts)."""
        records: list[dict] = []
        url = "https://api.eia.gov/v2/coal/shipments/receipts/data/"
        params = {
            "api_key": api_key,
            "frequency": "monthly",
            "data[0]": "price",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 100,
        }

        try:
            resp = await self.fetch_with_retry(url, params=params)
            data = resp.json()
            rows = data.get("response", {}).get("data", [])
            for row in rows:
                price = row.get("price")
                period = row.get("period")
                if price is None or period is None:
                    continue
                try:
                    price_val = float(price)
                except (ValueError, TypeError):
                    continue
                records.append({
                    "benchmark": "us_coal_receipts",
                    "price_usd": price_val,
                    "timestamp": f"{period}-01T00:00:00Z" if len(period) == 7 else period,
                    "source": "eia",
                })
            logger.info("EIA coal: retrieved %d price records", len(records))
        except Exception as exc:
            logger.error("EIA coal price fetch failed: %s", exc)

        return records

    # ------------------------------------------------------------------ #
    #  FRED helpers
    # ------------------------------------------------------------------ #
    async def _fetch_fred_henry_hub(self, api_key: str) -> list[dict]:
        """Fetch Henry Hub natural gas spot price from FRED (series DHHNGSP)."""
        records: list[dict] = []
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": "DHHNGSP",
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 500,
        }

        try:
            resp = await self.fetch_with_retry(url, params=params)
            data = resp.json()
            observations = data.get("observations", [])
            for obs in observations:
                val = obs.get("value", ".")
                if val == "." or val is None:
                    continue  # FRED uses "." for missing
                try:
                    price_val = float(val)
                except (ValueError, TypeError):
                    continue
                records.append({
                    "benchmark": "henry_hub",
                    "price": price_val,
                    "unit": "USD/MMBTU",
                    "timestamp": f"{obs['date']}T00:00:00Z",
                    "source": "fred",
                })
            logger.info("FRED Henry Hub: retrieved %d price records", len(records))
        except Exception as exc:
            logger.error("FRED Henry Hub fetch failed: %s", exc)

        return records
