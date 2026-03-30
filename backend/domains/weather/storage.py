"""
Weather domain storage.

Persists ENSO status and degree day records to their respective tables
and provides query methods for weather impact analysis.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from domains.base import BaseStorage

logger = logging.getLogger(__name__)


class WeatherStorage(BaseStorage):
    """Write and query weather data (degree days and ENSO status)."""

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
                        if table == "enso_status":
                            await session.execute(
                                text("""
                                    INSERT OR REPLACE INTO enso_status
                                        (oni_value, phase, period_date, source)
                                    VALUES
                                        (:oni_value, :phase, :period_date, :source)
                                """),
                                {
                                    "oni_value": rec["oni_value"],
                                    "phase": rec["phase"],
                                    "period_date": rec["period_date"],
                                    "source": rec.get("source", "noaa"),
                                },
                            )
                            stored += 1

                        elif table == "degree_days":
                            await session.execute(
                                text("""
                                    INSERT OR REPLACE INTO degree_days
                                        (region, hdd, cdd, deviation_from_normal,
                                         period_date, source)
                                    VALUES
                                        (:region, :hdd, :cdd, :deviation_from_normal,
                                         :period_date, :source)
                                """),
                                {
                                    "region": rec["region"],
                                    "hdd": rec.get("hdd"),
                                    "cdd": rec.get("cdd"),
                                    "deviation_from_normal": rec.get(
                                        "deviation_from_normal"
                                    ),
                                    "period_date": rec["period_date"],
                                    "source": rec.get("source", "noaa"),
                                },
                            )
                            stored += 1

                        else:
                            logger.warning(
                                "Unknown table in weather record: %s", table
                            )

                    except Exception as exc:
                        logger.error(
                            "Failed to store weather record (%s): %s", table, exc
                        )

        logger.info("WeatherStorage: stored %d / %d records", stored, len(records))
        return stored

    # ------------------------------------------------------------------ #
    #  Query
    # ------------------------------------------------------------------ #
    async def query(self, filters: dict, timeframe: str = "1Y") -> list[dict[str, Any]]:
        """Query weather data.

        Supported filter keys:
            table  - "degree_days" or "enso_status" (default: "degree_days")
            region - filter degree_days by region
        """
        table = filters.get("table", "degree_days")
        days = self.timeframe_to_days(timeframe)

        if table == "enso_status":
            return await self._query_enso(days)
        else:
            region = filters.get("region")
            return await self._query_degree_days(region, days)

    async def _query_enso(self, days: int) -> list[dict[str, Any]]:
        async with self.db.session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT oni_value, phase, period_date, source
                    FROM enso_status
                    WHERE period_date >= date('now', :offset)
                    ORDER BY period_date ASC
                """),
                {"offset": f"-{days} days"},
            )
            return [
                {
                    "oni_value": r[0],
                    "phase": r[1],
                    "period_date": r[2],
                    "source": r[3],
                }
                for r in result.fetchall()
            ]

    async def _query_degree_days(
        self, region: str | None, days: int
    ) -> list[dict[str, Any]]:
        where_clauses = ["period_date >= date('now', :offset)"]
        params: dict[str, Any] = {"offset": f"-{days} days"}

        if region:
            where_clauses.append("region = :region")
            params["region"] = region

        where_sql = " AND ".join(where_clauses)

        async with self.db.session_factory() as session:
            result = await session.execute(
                text(f"""
                    SELECT region, hdd, cdd, deviation_from_normal,
                           period_date, source
                    FROM degree_days
                    WHERE {where_sql}
                    ORDER BY period_date ASC
                """),
                params,
            )
            return [
                {
                    "region": r[0],
                    "hdd": r[1],
                    "cdd": r[2],
                    "deviation_from_normal": r[3],
                    "period_date": r[4],
                    "source": r[5],
                }
                for r in result.fetchall()
            ]
