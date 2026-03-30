"""
Sentiment domain storage.

Persists news headline records with sentiment scores to the news_headlines
table, avoiding duplicates by URL. Provides query methods for date range
and sentiment aggregation.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from domains.base import BaseStorage

logger = logging.getLogger(__name__)


class SentimentStorage(BaseStorage):
    """Write and query news headline sentiment data."""

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
                        if table == "news_headlines":
                            # Avoid duplicates by checking URL first
                            url = rec.get("url", "")
                            if url:
                                exists = await session.execute(
                                    text(
                                        "SELECT id FROM news_headlines "
                                        "WHERE url = :url LIMIT 1"
                                    ),
                                    {"url": url},
                                )
                                if exists.fetchone():
                                    continue

                            await session.execute(
                                text("""
                                    INSERT INTO news_headlines
                                        (title, url, source_name, published_at,
                                         sentiment_score, relevance_tag,
                                         tickers_mentioned)
                                    VALUES
                                        (:title, :url, :source_name, :published_at,
                                         :sentiment_score, :relevance_tag,
                                         :tickers_mentioned)
                                """),
                                {
                                    "title": rec["title"],
                                    "url": rec.get("url", ""),
                                    "source_name": rec.get("source_name", "unknown"),
                                    "published_at": rec.get("published_at", ""),
                                    "sentiment_score": rec.get("sentiment_score"),
                                    "relevance_tag": rec.get("relevance_tag"),
                                    "tickers_mentioned": rec.get("tickers_mentioned"),
                                },
                            )
                            stored += 1

                        else:
                            logger.warning(
                                "Unknown table in sentiment record: %s", table
                            )

                    except Exception as exc:
                        logger.error(
                            "Failed to store sentiment record (%s): %s", table, exc
                        )

        logger.info("SentimentStorage: stored %d / %d records", stored, len(records))
        return stored

    # ------------------------------------------------------------------ #
    #  Query
    # ------------------------------------------------------------------ #
    async def query(self, filters: dict, timeframe: str = "1M") -> list[dict[str, Any]]:
        """Query news headlines.

        Supported filter keys:
            limit - maximum number of headlines to return (default: 50)
        """
        days = self.timeframe_to_days(timeframe)
        limit = filters.get("limit", 50)

        async with self.db.session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT title, url, source_name, published_at,
                           sentiment_score, relevance_tag, tickers_mentioned
                    FROM news_headlines
                    WHERE published_at >= datetime('now', :offset)
                    ORDER BY published_at DESC
                    LIMIT :limit
                """),
                {"offset": f"-{days} days", "limit": limit},
            )
            rows = result.fetchall()

        return [
            {
                "title": r[0],
                "url": r[1],
                "source_name": r[2],
                "published_at": r[3],
                "sentiment_score": r[4],
                "relevance_tag": r[5],
                "tickers_mentioned": r[6],
            }
            for r in rows
        ]
