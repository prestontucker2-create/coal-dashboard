"""
Supply domain storage -- persists production and inventory records into
``us_coal_production`` and ``coal_inventories`` tables.
"""

from typing import Any
import logging

from sqlalchemy import text

from domains.base import BaseStorage

logger = logging.getLogger(__name__)


class SupplyStorage(BaseStorage):
    """Read / write US coal production and inventory data."""

    # ----- write -----------------------------------------------------------

    async def store(self, records: list[dict[str, Any]]) -> int:
        """
        INSERT OR REPLACE production and inventory records.

        Each record must carry a ``_table`` key (``"production"`` or
        ``"inventory"``) so we route it to the correct table.
        """
        if not records:
            return 0

        prod_records = [r for r in records if r.get("_table") == "production"]
        inv_records = [r for r in records if r.get("_table") == "inventory"]

        inserted = 0
        async with self.db.session_factory() as session:
            async with session.begin():
                inserted += await self._store_production(session, prod_records)
                inserted += await self._store_inventories(session, inv_records)

        logger.info(
            "SupplyStorage stored %d records (%d production, %d inventory)",
            inserted,
            len(prod_records),
            len(inv_records),
        )
        return inserted

    async def _store_production(self, session, records: list[dict]) -> int:
        count = 0
        for rec in records:
            await session.execute(
                text("""
                    INSERT OR REPLACE INTO us_coal_production
                        (region, production_tons, period_type, period_date, source)
                    VALUES
                        (:region, :production_tons, :period_type, :period_date, :source)
                """),
                {
                    "region": rec["region"],
                    "production_tons": rec["production_tons"],
                    "period_type": rec["period_type"],
                    "period_date": rec["period_date"],
                    "source": rec.get("source", "eia"),
                },
            )
            count += 1
        return count

    async def _store_inventories(self, session, records: list[dict]) -> int:
        count = 0
        for rec in records:
            await session.execute(
                text("""
                    INSERT OR REPLACE INTO coal_inventories
                        (location, inventory_tons, days_supply, period_date, source)
                    VALUES
                        (:location, :inventory_tons, :days_supply, :period_date, :source)
                """),
                {
                    "location": rec["location"],
                    "inventory_tons": rec["inventory_tons"],
                    "days_supply": rec.get("days_supply"),
                    "period_date": rec["period_date"],
                    "source": rec.get("source", "eia"),
                },
            )
            count += 1
        return count

    # ----- read ------------------------------------------------------------

    async def query(
        self,
        filters: dict,
        timeframe: str = "1Y",
    ) -> list[dict[str, Any]]:
        """
        Generic query dispatcher.

        ``filters`` should contain a ``"table"`` key (``"production"`` or
        ``"inventories"``) to determine which table to read.  Optional
        keys: ``region``.
        """
        table = filters.get("table", "production")
        if table == "inventories":
            return await self._query_inventories(filters, timeframe)
        return await self._query_production(filters, timeframe)

    async def _query_production(
        self,
        filters: dict,
        timeframe: str,
    ) -> list[dict[str, Any]]:
        days = self.timeframe_to_days(timeframe)
        region = filters.get("region", "total")

        clauses = ["period_date >= date('now', :offset)"]
        params: dict[str, Any] = {"offset": f"-{days} days"}

        if region and region.lower() != "total":
            clauses.append("LOWER(region) = LOWER(:region)")
            params["region"] = region

        where = " AND ".join(clauses)

        async with self.db.session_factory() as session:
            result = await session.execute(
                text(f"""
                    SELECT region, production_tons, period_type,
                           period_date, source
                    FROM us_coal_production
                    WHERE {where}
                    ORDER BY period_date DESC
                """),
                params,
            )
            rows = result.fetchall()

        return [
            {
                "region": r[0],
                "production_tons": r[1],
                "period_type": r[2],
                "period_date": r[3],
                "source": r[4],
            }
            for r in rows
        ]

    async def _query_inventories(
        self,
        filters: dict,
        timeframe: str,
    ) -> list[dict[str, Any]]:
        days = self.timeframe_to_days(timeframe)
        params: dict[str, Any] = {"offset": f"-{days} days"}

        location = filters.get("location")
        clauses = ["period_date >= date('now', :offset)"]
        if location:
            clauses.append("LOWER(location) = LOWER(:location)")
            params["location"] = location

        where = " AND ".join(clauses)

        async with self.db.session_factory() as session:
            result = await session.execute(
                text(f"""
                    SELECT location, inventory_tons, days_supply,
                           period_date, source
                    FROM coal_inventories
                    WHERE {where}
                    ORDER BY period_date DESC
                """),
                params,
            )
            rows = result.fetchall()

        return [
            {
                "location": r[0],
                "inventory_tons": r[1],
                "days_supply": r[2],
                "period_date": r[3],
                "source": r[4],
            }
            for r in rows
        ]
