"""
Sentiment domain API routes.

Mounted at /api/sentiment by main.py.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from sqlalchemy import text

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_db():
    """Lazy import to avoid circular dependency at module load time."""
    from main import _db
    return _db


def _timeframe_to_days(timeframe: str) -> int:
    mapping = {
        "1W": 7, "2W": 14, "1M": 30, "3M": 90, "6M": 180,
        "1Y": 365, "3Y": 1095, "ALL": 36500,
        "7d": 7, "14d": 14, "30d": 30, "90d": 90,
    }
    return mapping.get(timeframe, 7)


# ------------------------------------------------------------------ #
#  GET /news  --  recent headlines with sentiment
# ------------------------------------------------------------------ #
@router.get("/news")
async def get_news(
    timeframe: str = Query("7d", description="Lookback: 7d, 14d, 30d, 1W, 1M, 3M, etc."),
    limit: int = Query(50, description="Max headlines to return", ge=1, le=500),
):
    """Return recent coal-related news headlines with sentiment scores."""
    db = _get_db()
    days = _timeframe_to_days(timeframe)

    async with db.session_factory() as session:
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
        rows = [
            {
                "title": r[0],
                "url": r[1],
                "source_name": r[2],
                "published_at": r[3],
                "sentiment_score": r[4],
                "relevance_tag": r[5],
                "tickers_mentioned": r[6],
            }
            for r in result.fetchall()
        ]

    return {"timeframe": timeframe, "count": len(rows), "data": rows}


# ------------------------------------------------------------------ #
#  GET /summary  --  aggregate sentiment score
# ------------------------------------------------------------------ #
@router.get("/summary")
async def get_summary():
    """Return aggregate sentiment score and breakdown over recent headlines."""
    db = _get_db()

    async with db.session_factory() as session:
        # Overall sentiment for last 7 days
        overall_result = await session.execute(text("""
            SELECT
                COUNT(*) as total,
                AVG(sentiment_score) as avg_sentiment,
                SUM(CASE WHEN sentiment_score > 0.1 THEN 1 ELSE 0 END) as bullish_count,
                SUM(CASE WHEN sentiment_score < -0.1 THEN 1 ELSE 0 END) as bearish_count,
                SUM(CASE WHEN sentiment_score BETWEEN -0.1 AND 0.1 THEN 1 ELSE 0 END) as neutral_count
            FROM news_headlines
            WHERE published_at >= datetime('now', '-7 days')
        """))
        overall = overall_result.fetchone()

        # Sentiment by relevance tag
        by_tag_result = await session.execute(text("""
            SELECT
                relevance_tag,
                COUNT(*) as count,
                AVG(sentiment_score) as avg_sentiment
            FROM news_headlines
            WHERE published_at >= datetime('now', '-7 days')
              AND relevance_tag IS NOT NULL
            GROUP BY relevance_tag
            ORDER BY count DESC
        """))
        by_tag = [
            {
                "tag": r[0],
                "count": r[1],
                "avg_sentiment": round(r[2], 3) if r[2] is not None else None,
            }
            for r in by_tag_result.fetchall()
        ]

        # Most mentioned tickers
        ticker_result = await session.execute(text("""
            SELECT tickers_mentioned, COUNT(*) as mention_count
            FROM news_headlines
            WHERE published_at >= datetime('now', '-7 days')
              AND tickers_mentioned IS NOT NULL
              AND tickers_mentioned != ''
            GROUP BY tickers_mentioned
            ORDER BY mention_count DESC
            LIMIT 10
        """))
        ticker_rows = ticker_result.fetchall()

    # Aggregate ticker mentions (headlines may have multiple tickers)
    ticker_counts: dict[str, int] = {}
    for row in ticker_rows:
        tickers_str = row[0]
        count = row[1]
        for ticker in tickers_str.split(","):
            ticker = ticker.strip()
            if ticker:
                ticker_counts[ticker] = ticker_counts.get(ticker, 0) + count

    top_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    total = overall[0] if overall else 0
    avg_sentiment = round(overall[1], 3) if overall and overall[1] is not None else None

    # Determine overall market mood label
    mood = "neutral"
    if avg_sentiment is not None:
        if avg_sentiment > 0.15:
            mood = "bullish"
        elif avg_sentiment < -0.15:
            mood = "bearish"

    return {
        "period": "7d",
        "total_headlines": total,
        "avg_sentiment": avg_sentiment,
        "mood": mood,
        "bullish_count": overall[2] if overall else 0,
        "bearish_count": overall[3] if overall else 0,
        "neutral_count": overall[4] if overall else 0,
        "by_relevance": by_tag,
        "top_tickers": [
            {"ticker": t, "mentions": c} for t, c in top_tickers
        ],
    }
