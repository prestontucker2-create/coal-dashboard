import logging
from typing import Any

from sqlalchemy import text

from domains.base import BaseStorage

logger = logging.getLogger(__name__)


class MacroStorage(BaseStorage):
    """Stores and queries macro indicator records in the macro_indicators table."""

    async def store(self, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0

        inserted = 0
        async with self.db.session_factory() as session:
            async with session.begin():
                for rec in records:
                    await session.execute(
                        text("""
                            INSERT OR REPLACE INTO macro_indicators
                                (indicator, value, timestamp, source)
                            VALUES
                                (:indicator, :value, :timestamp, :source)
                        """),
                        {
                            "indicator": rec["indicator"],
                            "value": rec["value"],
                            "timestamp": rec["timestamp"],
                            "source": rec.get("source", "fred"),
                        },
                    )
                    inserted += 1

        logger.info(f"MacroStorage: upserted {inserted} records")
        return inserted

    async def query(self, filters: dict, timeframe: str = "1Y") -> list[dict[str, Any]]:
        """Query macro indicators with optional filtering.

        Args:
            filters: dict that may contain:
                - names: list[str] of indicator slug names to include
            timeframe: one of 1W, 1M, 3M, 6M, 1Y, 3Y, ALL
        """
        days = self.timeframe_to_days(timeframe)

        conditions = ["timestamp >= date('now', :offset)"]
        params: dict[str, Any] = {"offset": f"-{days} days"}

        names = filters.get("names")
        if names:
            placeholders = ", ".join(f":n{i}" for i in range(len(names)))
            conditions.append(f"indicator IN ({placeholders})")
            for i, name in enumerate(names):
                params[f"n{i}"] = name

        where_clause = " AND ".join(conditions)

        async with self.db.session_factory() as session:
            result = await session.execute(
                text(f"""
                    SELECT indicator, value, timestamp, source
                    FROM macro_indicators
                    WHERE {where_clause}
                    ORDER BY indicator, timestamp DESC
                """),
                params,
            )
            rows = result.fetchall()

        return [
            {
                "indicator": row[0],
                "value": row[1],
                "timestamp": row[2],
                "source": row[3],
            }
            for row in rows
        ]
