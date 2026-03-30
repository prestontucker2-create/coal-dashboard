"""
Demand domain storage.

Persists electricity generation records to the power_generation table
and provides query methods for region/fuel_type filtering.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from domains.base import BaseStorage

logger = logging.getLogger(__name__)


class DemandStorage(BaseStorage):
    """Write and query power generation data."""

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
                        if table == "power_generation":
                            await session.execute(
                                text("""
                                    INSERT OR REPLACE INTO power_generation
                                        (region, fuel_type, generation_mwh,
                                         period_type, period_date, source)
                                    VALUES
                                        (:region, :fuel_type, :generation_mwh,
                                         :period_type, :period_date, :source)
                                """),
                                {
                                    "region": rec["region"],
                                    "fuel_type": rec["fuel_type"],
                                    "generation_mwh": rec["generation_mwh"],
                                    "period_type": rec["period_type"],
                                    "period_date": rec["period_date"],
                                    "source": rec.get("source", "eia"),
                                },
                            )
                            stored += 1
                        else:
                            logger.warning("Unknown table in demand record: %s", table)

                    except Exception as exc:
                        logger.error(
                            "Failed to store demand record (%s): %s", table, exc
                        )

        logger.info("DemandStorage: stored %d / %d records", stored, len(records))
        return stored

    # ------------------------------------------------------------------ #
    #  Query
    # ------------------------------------------------------------------ #
    async def query(self, filters: dict, timeframe: str = "1Y") -> list[dict[str, Any]]:
        """Query power generation data.

        Supported filter keys:
            region    - filter by region (e.g. 'US', state name)
            fuel_type - filter by fuel type (e.g. 'coal', 'natural_gas')
        """
        region = filters.get("region")
        fuel_type = filters.get("fuel_type")
        days = self.timeframe_to_days(timeframe)

        where_clauses = ["period_date >= date('now', :offset)"]
        params: dict[str, Any] = {"offset": f"-{days} days"}

        if region:
            where_clauses.append("region = :region")
            params["region"] = region
        if fuel_type:
            where_clauses.append("fuel_type = :fuel_type")
            params["fuel_type"] = fuel_type

        where_sql = " AND ".join(where_clauses)

        async with self.db.session_factory() as session:
            result = await session.execute(
                text(f"""
                    SELECT region, fuel_type, generation_mwh,
                           period_type, period_date, source
                    FROM power_generation
                    WHERE {where_sql}
                    ORDER BY period_date ASC
                """),
                params,
            )
            rows = result.fetchall()

        return [
            {
                "region": r[0],
                "fuel_type": r[1],
                "generation_mwh": r[2],
                "period_type": r[3],
                "period_date": r[4],
                "source": r[5],
            }
            for r in rows
        ]
