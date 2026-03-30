"""
Trade flows domain storage.

Persists coal trade flow records to the trade_flows table and provides
query methods for trade analysis and map visualization data.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from domains.base import BaseStorage

logger = logging.getLogger(__name__)


class TradeFlowStorage(BaseStorage):
    """Write and query coal trade flow data."""

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
                        if table == "trade_flows":
                            await session.execute(
                                text("""
                                    INSERT OR REPLACE INTO trade_flows
                                        (exporter, importer, coal_type,
                                         volume_mt, value_usd, period_date, source)
                                    VALUES
                                        (:exporter, :importer, :coal_type,
                                         :volume_mt, :value_usd, :period_date, :source)
                                """),
                                {
                                    "exporter": rec["exporter"],
                                    "importer": rec["importer"],
                                    "coal_type": rec["coal_type"],
                                    "volume_mt": rec["volume_mt"],
                                    "value_usd": rec.get("value_usd"),
                                    "period_date": rec["period_date"],
                                    "source": rec.get("source", "eia"),
                                },
                            )
                            stored += 1
                        else:
                            logger.warning(
                                "Unknown table in trade flow record: %s", table
                            )

                    except Exception as exc:
                        logger.error(
                            "Failed to store trade flow record (%s): %s",
                            table, exc,
                        )

        logger.info(
            "TradeFlowStorage: stored %d / %d records", stored, len(records)
        )
        return stored

    # ------------------------------------------------------------------ #
    #  Query
    # ------------------------------------------------------------------ #
    async def query(self, filters: dict, timeframe: str = "1Y") -> list[dict[str, Any]]:
        """Query trade flow data.

        Supported filter keys:
            exporter  - filter by exporting country (default: all)
            importer  - filter by importing country/region
            coal_type - filter by coal type
        """
        days = self.timeframe_to_days(timeframe)

        where_clauses = ["period_date >= date('now', :offset)"]
        params: dict[str, Any] = {"offset": f"-{days} days"}

        exporter = filters.get("exporter")
        if exporter:
            where_clauses.append("exporter = :exporter")
            params["exporter"] = exporter

        importer = filters.get("importer")
        if importer:
            where_clauses.append("importer = :importer")
            params["importer"] = importer

        coal_type = filters.get("coal_type")
        if coal_type:
            where_clauses.append("coal_type = :coal_type")
            params["coal_type"] = coal_type

        where_sql = " AND ".join(where_clauses)

        async with self.db.session_factory() as session:
            result = await session.execute(
                text(f"""
                    SELECT exporter, importer, coal_type,
                           volume_mt, value_usd, period_date, source
                    FROM trade_flows
                    WHERE {where_sql}
                    ORDER BY period_date ASC
                """),
                params,
            )
            rows = result.fetchall()

        return [
            {
                "exporter": r[0],
                "importer": r[1],
                "coal_type": r[2],
                "volume_mt": r[3],
                "value_usd": r[4],
                "period_date": r[5],
                "source": r[6],
            }
            for r in rows
        ]
