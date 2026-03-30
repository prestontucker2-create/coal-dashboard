import logging
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import text

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_db():
    """Lazy import to avoid circular imports at module load time."""
    from main import _db
    return _db


@router.get("/indicators")
async def get_indicators(
    names: Optional[str] = Query(None, description="Comma-separated indicator slugs (e.g. audusd,dxy,us10y)"),
    timeframe: str = Query("6M", description="Timeframe: 1W, 1M, 3M, 6M, 1Y, 3Y, ALL"),
):
    """Return macro indicator time-series data, optionally filtered by name and timeframe."""
    db = _get_db()

    days_map = {
        "1W": 7, "1M": 30, "3M": 90, "6M": 180,
        "1Y": 365, "3Y": 1095, "ALL": 36500,
    }
    days = days_map.get(timeframe, 180)

    conditions = ["timestamp >= date('now', :offset)"]
    params: dict = {"offset": f"-{days} days"}

    if names:
        name_list = [n.strip() for n in names.split(",") if n.strip()]
        if name_list:
            placeholders = ", ".join(f":n{i}" for i in range(len(name_list)))
            conditions.append(f"indicator IN ({placeholders})")
            for i, name in enumerate(name_list):
                params[f"n{i}"] = name

    where_clause = " AND ".join(conditions)

    async with db.session_factory() as session:
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

    indicators: dict[str, list] = {}
    for row in rows:
        slug = row[0]
        if slug not in indicators:
            indicators[slug] = []
        indicators[slug].append({
            "value": row[1],
            "timestamp": row[2],
            "source": row[3],
        })

    return {"indicators": indicators, "timeframe": timeframe, "count": len(rows)}


@router.get("/latest")
async def get_latest():
    """Return the most recent value for each macro indicator."""
    db = _get_db()

    async with db.session_factory() as session:
        result = await session.execute(text("""
            SELECT indicator, value, timestamp, source
            FROM macro_indicators
            WHERE id IN (
                SELECT MAX(id) FROM macro_indicators GROUP BY indicator
            )
            ORDER BY indicator
        """))
        rows = result.fetchall()

    return {
        "indicators": [
            {
                "indicator": row[0],
                "value": row[1],
                "timestamp": row[2],
                "source": row[3],
            }
            for row in rows
        ]
    }


@router.get("/cot")
async def get_cot(
    timeframe: str = Query("1Y", description="Timeframe: 1W, 1M, 3M, 6M, 1Y, 3Y, ALL"),
):
    """Return COT (Commitments of Traders) positioning data.

    Placeholder endpoint -- returns data from the cot_positions table if
    available, or an empty list otherwise.
    """
    db = _get_db()

    days_map = {
        "1W": 7, "1M": 30, "3M": 90, "6M": 180,
        "1Y": 365, "3Y": 1095, "ALL": 36500,
    }
    days = days_map.get(timeframe, 365)

    async with db.session_factory() as session:
        result = await session.execute(
            text("""
                SELECT contract, long_positions, short_positions,
                       net_position, change_week, report_date
                FROM cot_positions
                WHERE report_date >= date('now', :offset)
                ORDER BY report_date DESC
            """),
            {"offset": f"-{days} days"},
        )
        rows = result.fetchall()

    return {
        "positions": [
            {
                "contract": row[0],
                "long_positions": row[1],
                "short_positions": row[2],
                "net_position": row[3],
                "change_week": row[4],
                "report_date": row[5],
            }
            for row in rows
        ],
        "timeframe": timeframe,
    }
