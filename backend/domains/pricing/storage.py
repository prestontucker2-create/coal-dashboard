"""
Pricing domain storage.

Persists coal prices, gas prices, and derived price spreads to SQLite.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from domains.base import BaseStorage

logger = logging.getLogger(__name__)


class PricingStorage(BaseStorage):
    """Write and query pricing data."""

    # ------------------------------------------------------------------ #
    #  Store
    # ------------------------------------------------------------------ #
    async def store(self, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0

        stored = 0
        async with self.db.session_factory() as session:
            async with session.begin():
                for rec in records:
                    table = rec.get("_table")
                    try:
                        if table == "coal_prices":
                            await session.execute(
                                text("""
                                    INSERT OR REPLACE INTO coal_prices
                                        (benchmark, price_usd, currency, timestamp, source)
                                    VALUES
                                        (:benchmark, :price_usd, :currency, :timestamp, :source)
                                """),
                                {
                                    "benchmark": rec["benchmark"],
                                    "price_usd": rec["price_usd"],
                                    "currency": rec.get("currency", "USD"),
                                    "timestamp": rec["timestamp"],
                                    "source": rec["source"],
                                },
                            )
                            stored += 1

                        elif table == "gas_prices":
                            await session.execute(
                                text("""
                                    INSERT OR REPLACE INTO gas_prices
                                        (benchmark, price, unit, timestamp, source)
                                    VALUES
                                        (:benchmark, :price, :unit, :timestamp, :source)
                                """),
                                {
                                    "benchmark": rec["benchmark"],
                                    "price": rec["price"],
                                    "unit": rec.get("unit", "USD/MMBTU"),
                                    "timestamp": rec["timestamp"],
                                    "source": rec["source"],
                                },
                            )
                            stored += 1

                        elif table == "price_spreads":
                            await session.execute(
                                text("""
                                    INSERT OR REPLACE INTO price_spreads
                                        (spread_name, value, timestamp)
                                    VALUES
                                        (:spread_name, :value, :timestamp)
                                """),
                                {
                                    "spread_name": rec["spread_name"],
                                    "value": rec["value"],
                                    "timestamp": rec["timestamp"],
                                },
                            )
                            stored += 1

                        else:
                            logger.warning("Unknown table in record: %s", table)

                    except Exception as exc:
                        logger.error("Failed to store pricing record (%s): %s", table, exc)

        logger.info("PricingStorage: stored %d / %d records", stored, len(records))
        return stored

    # ------------------------------------------------------------------ #
    #  Query
    # ------------------------------------------------------------------ #
    async def query(self, filters: dict, timeframe: str = "1Y") -> list[dict[str, Any]]:
        """Query pricing data.

        Supported filter keys:
            table     - "coal_prices", "gas_prices", or "price_spreads"
            benchmark - filter by benchmark name (coal/gas) or spread_name
        """
        table = filters.get("table", "coal_prices")
        benchmark = filters.get("benchmark")
        days = self.timeframe_to_days(timeframe)

        results: list[dict[str, Any]] = []
        async with self.db.session_factory() as session:
            if table == "coal_prices":
                results = await self._query_coal(session, benchmark, days)
            elif table == "gas_prices":
                results = await self._query_gas(session, benchmark, days)
            elif table == "price_spreads":
                results = await self._query_spreads(session, benchmark, days)
            else:
                logger.warning("Unknown query table: %s", table)

        return results

    # ------------------------------------------------------------------ #
    #  Private query helpers
    # ------------------------------------------------------------------ #
    async def _query_coal(self, session, benchmark: str | None, days: int) -> list[dict]:
        where_clauses = ["timestamp >= datetime('now', :offset)"]
        params: dict[str, Any] = {"offset": f"-{days} days"}

        if benchmark:
            where_clauses.append("benchmark = :benchmark")
            params["benchmark"] = benchmark

        where_sql = " AND ".join(where_clauses)
        result = await session.execute(
            text(f"""
                SELECT benchmark, price_usd, currency, timestamp, source
                FROM coal_prices
                WHERE {where_sql}
                ORDER BY timestamp ASC
            """),
            params,
        )
        return [
            {
                "benchmark": r[0],
                "price_usd": r[1],
                "currency": r[2],
                "timestamp": r[3],
                "source": r[4],
            }
            for r in result.fetchall()
        ]

    async def _query_gas(self, session, benchmark: str | None, days: int) -> list[dict]:
        where_clauses = ["timestamp >= datetime('now', :offset)"]
        params: dict[str, Any] = {"offset": f"-{days} days"}

        if benchmark:
            where_clauses.append("benchmark = :benchmark")
            params["benchmark"] = benchmark

        where_sql = " AND ".join(where_clauses)
        result = await session.execute(
            text(f"""
                SELECT benchmark, price, unit, timestamp, source
                FROM gas_prices
                WHERE {where_sql}
                ORDER BY timestamp ASC
            """),
            params,
        )
        return [
            {
                "benchmark": r[0],
                "price": r[1],
                "unit": r[2],
                "timestamp": r[3],
                "source": r[4],
            }
            for r in result.fetchall()
        ]

    async def _query_spreads(self, session, spread_name: str | None, days: int) -> list[dict]:
        where_clauses = ["timestamp >= datetime('now', :offset)"]
        params: dict[str, Any] = {"offset": f"-{days} days"}

        if spread_name:
            where_clauses.append("spread_name = :spread_name")
            params["spread_name"] = spread_name

        where_sql = " AND ".join(where_clauses)
        result = await session.execute(
            text(f"""
                SELECT spread_name, value, timestamp
                FROM price_spreads
                WHERE {where_sql}
                ORDER BY timestamp ASC
            """),
            params,
        )
        return [
            {
                "spread_name": r[0],
                "value": r[1],
                "timestamp": r[2],
            }
            for r in result.fetchall()
        ]
