"""
Demand domain API routes.

Mounted at /api/demand by main.py.
"""

from __future__ import annotations

import logging
from typing import Optional

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
        "1W": 7, "1M": 30, "3M": 90, "6M": 180,
        "1Y": 365, "3Y": 1095, "ALL": 36500,
    }
    return mapping.get(timeframe, 365)


# ------------------------------------------------------------------ #
#  GET /generation  --  generation time-series by fuel type
# ------------------------------------------------------------------ #
@router.get("/generation")
async def get_generation(
    region: Optional[str] = Query(None, description="Filter by region (e.g. 'US')"),
    fuel_type: Optional[str] = Query(None, description="Filter by fuel type (e.g. 'coal', 'natural_gas')"),
    timeframe: str = Query("1Y", description="Lookback window: 1W, 1M, 3M, 6M, 1Y, 3Y, ALL"),
):
    """Return electricity generation time-series, optionally filtered by region and fuel type."""
    db = _get_db()
    days = _timeframe_to_days(timeframe)

    where_clauses = ["period_date >= date('now', :offset)"]
    params: dict = {"offset": f"-{days} days"}

    if region:
        where_clauses.append("region = :region")
        params["region"] = region
    if fuel_type:
        where_clauses.append("fuel_type = :fuel_type")
        params["fuel_type"] = fuel_type

    where_sql = " AND ".join(where_clauses)

    async with db.session_factory() as session:
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
        rows = [
            {
                "region": r[0],
                "fuel_type": r[1],
                "generation_mwh": r[2],
                "period_type": r[3],
                "period_date": r[4],
                "source": r[5],
            }
            for r in result.fetchall()
        ]

    return {"timeframe": timeframe, "count": len(rows), "data": rows}


# ------------------------------------------------------------------ #
#  GET /summary  --  latest generation mix snapshot
# ------------------------------------------------------------------ #
@router.get("/summary")
async def get_summary():
    """Return the latest generation mix snapshot -- most recent period per fuel type."""
    db = _get_db()

    async with db.session_factory() as session:
        # Get the most recent period_date in the data
        latest_result = await session.execute(text("""
            SELECT MAX(period_date) FROM power_generation
        """))
        latest_row = latest_result.fetchone()
        latest_period = latest_row[0] if latest_row else None

        if not latest_period:
            return {"period": None, "mix": [], "coal_share_pct": None}

        # Get generation for each fuel type at the latest period
        result = await session.execute(
            text("""
                SELECT fuel_type, SUM(generation_mwh) as total_mwh
                FROM power_generation
                WHERE period_date = :period
                GROUP BY fuel_type
                ORDER BY total_mwh DESC
            """),
            {"period": latest_period},
        )
        rows = result.fetchall()

    mix = []
    total_generation = 0.0
    coal_generation = 0.0

    for r in rows:
        fuel = r[0]
        mwh = r[1] or 0.0
        mix.append({"fuel_type": fuel, "generation_mwh": mwh})
        if fuel != "total":
            total_generation += mwh
        if fuel == "coal":
            coal_generation = mwh

    # Calculate coal share -- use 'total' row if available, otherwise sum
    total_row = next((m for m in mix if m["fuel_type"] == "total"), None)
    denominator = total_row["generation_mwh"] if total_row and total_row["generation_mwh"] else total_generation

    coal_share_pct = None
    if denominator and denominator > 0:
        coal_share_pct = round((coal_generation / denominator) * 100, 2)

    return {
        "period": latest_period,
        "mix": mix,
        "coal_share_pct": coal_share_pct,
    }
