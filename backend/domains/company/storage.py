import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from domains.base import BaseStorage

logger = logging.getLogger(__name__)


class CompanyStorage(BaseStorage):
    """Persists and queries stock price data in the stock_prices table."""

    async def store(self, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0

        async with self.db.session_factory() as session:
            async with session.begin():
                for row in records:
                    await session.execute(
                        text("""
                            INSERT OR REPLACE INTO stock_prices
                                (ticker, date, open, high, low, close, volume, adj_close)
                            VALUES
                                (:ticker, :date, :open, :high, :low, :close, :volume, :adj_close)
                        """),
                        {
                            "ticker": row["ticker"],
                            "date": row["date"],
                            "open": row.get("open"),
                            "high": row.get("high"),
                            "low": row.get("low"),
                            "close": row["close"],
                            "volume": row.get("volume"),
                            "adj_close": row.get("adj_close"),
                        },
                    )

        logger.info(f"Stored {len(records)} stock price records")
        return len(records)

    async def query(self, filters: dict, timeframe: str = "1Y") -> list[dict[str, Any]]:
        days = self.timeframe_to_days(timeframe)
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        conditions = ["date >= :start_date"]
        params: dict[str, Any] = {"start_date": start_date}

        tickers = filters.get("tickers")
        if tickers:
            placeholders = ", ".join(f":t{i}" for i in range(len(tickers)))
            conditions.append(f"ticker IN ({placeholders})")
            for i, t in enumerate(tickers):
                params[f"t{i}"] = t

        where_clause = " AND ".join(conditions)

        async with self.db.session_factory() as session:
            result = await session.execute(
                text(f"""
                    SELECT ticker, date, open, high, low, close, volume, adj_close
                    FROM stock_prices
                    WHERE {where_clause}
                    ORDER BY ticker, date
                """),
                params,
            )
            rows = result.fetchall()

        return [
            {
                "ticker": r[0],
                "date": r[1],
                "open": r[2],
                "high": r[3],
                "low": r[4],
                "close": r[5],
                "volume": r[6],
                "adj_close": r[7],
            }
            for r in rows
        ]
