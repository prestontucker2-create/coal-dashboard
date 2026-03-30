"""
Pricing domain processor.

Transforms raw coal and gas price data into storage-ready records and
calculates derived spreads (gas-to-coal ratio).
"""

from __future__ import annotations

import logging
from typing import Any

from domains.base import BaseProcessor

logger = logging.getLogger(__name__)

# Approximate energy-content conversion factors.
# 1 short ton of thermal coal ~ 20 MMBTU (varies by rank).
COAL_MMBTU_PER_TON = 20.0


class PricingProcessor(BaseProcessor):
    """Clean, normalise, and enrich pricing data."""

    def process(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []

        coal_prices = raw_data.get("coal_prices", [])
        gas_prices = raw_data.get("gas_prices", [])

        # ---- coal prices ------------------------------------------------
        for cp in coal_prices:
            if cp.get("price_usd") is None:
                # Skip placeholder / missing records
                continue
            records.append({
                "_table": "coal_prices",
                "benchmark": self._normalise_benchmark(cp.get("benchmark", "")),
                "price_usd": round(float(cp["price_usd"]), 2),
                "currency": "USD",
                "timestamp": cp.get("timestamp", ""),
                "source": cp.get("source", "unknown"),
            })

        # ---- gas prices -------------------------------------------------
        for gp in gas_prices:
            if gp.get("price") is None:
                continue
            records.append({
                "_table": "gas_prices",
                "benchmark": self._normalise_benchmark(gp.get("benchmark", "")),
                "price": round(float(gp["price"]), 4),
                "unit": gp.get("unit", "USD/MMBTU"),
                "timestamp": gp.get("timestamp", ""),
                "source": gp.get("source", "unknown"),
            })

        # ---- derived spreads --------------------------------------------
        records.extend(self._compute_spreads(coal_prices, gas_prices))

        logger.info("PricingProcessor produced %d records", len(records))
        return records

    # ------------------------------------------------------------------ #
    #  Spread calculation
    # ------------------------------------------------------------------ #
    def _compute_spreads(
        self,
        coal_prices: list[dict],
        gas_prices: list[dict],
    ) -> list[dict[str, Any]]:
        """Compute gas/coal switching ratio.

        The gas-coal ratio expresses the Henry Hub price relative to the
        Newcastle coal price *on a per-MMBTU basis*.

        Ratio = henry_hub_price / (newcastle_price / COAL_MMBTU_PER_TON)

        A ratio > 1 implies gas is more expensive per unit of energy than
        coal (bullish for coal demand); < 1 implies gas is cheaper.
        """
        spreads: list[dict[str, Any]] = []

        # Build lookup: latest price per benchmark
        latest_coal: dict[str, tuple[float, str]] = {}
        for cp in coal_prices:
            bm = self._normalise_benchmark(cp.get("benchmark", ""))
            if cp.get("price_usd") is None:
                continue
            ts = cp.get("timestamp", "")
            # Keep latest by simple string comparison (ISO timestamps)
            if bm not in latest_coal or ts > latest_coal[bm][1]:
                latest_coal[bm] = (float(cp["price_usd"]), ts)

        latest_gas: dict[str, tuple[float, str]] = {}
        for gp in gas_prices:
            bm = self._normalise_benchmark(gp.get("benchmark", ""))
            if gp.get("price") is None:
                continue
            ts = gp.get("timestamp", "")
            if bm not in latest_gas or ts > latest_gas[bm][1]:
                latest_gas[bm] = (float(gp["price"]), ts)

        # Newcastle coal vs Henry Hub
        newcastle = latest_coal.get("newcastle")
        henry_hub = latest_gas.get("henry_hub")

        if newcastle and henry_hub:
            coal_price_per_ton, coal_ts = newcastle
            gas_price_mmbtu, gas_ts = henry_hub

            if coal_price_per_ton > 0:
                coal_per_mmbtu = coal_price_per_ton / COAL_MMBTU_PER_TON
                ratio = gas_price_mmbtu / coal_per_mmbtu
                # Use the more recent of the two timestamps
                ts = max(coal_ts, gas_ts)
                spreads.append({
                    "_table": "price_spreads",
                    "spread_name": "gas_coal_ratio",
                    "value": round(ratio, 4),
                    "timestamp": ts,
                })
                logger.info(
                    "Gas/coal ratio: %.4f  (gas $%.2f/MMBTU vs coal $%.2f/MMBTU)",
                    ratio,
                    gas_price_mmbtu,
                    coal_per_mmbtu,
                )

        # US coal receipts vs Henry Hub (domestic switching metric)
        us_coal = latest_coal.get("us_coal_receipts")
        if us_coal and henry_hub:
            coal_price_per_ton, coal_ts = us_coal
            gas_price_mmbtu, gas_ts = henry_hub

            if coal_price_per_ton > 0:
                coal_per_mmbtu = coal_price_per_ton / COAL_MMBTU_PER_TON
                ratio = gas_price_mmbtu / coal_per_mmbtu
                ts = max(coal_ts, gas_ts)
                spreads.append({
                    "_table": "price_spreads",
                    "spread_name": "gas_us_coal_ratio",
                    "value": round(ratio, 4),
                    "timestamp": ts,
                })

        return spreads

    # ------------------------------------------------------------------ #
    #  Utilities
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalise_benchmark(name: str) -> str:
        return name.strip().lower().replace(" ", "_")
