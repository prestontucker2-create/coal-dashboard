"""
Trade flows domain API routes.

Mounted at /api/trade-flows by main.py.
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
#  GET /us  --  US trade flow data
# ------------------------------------------------------------------ #
@router.get("/us")
async def get_us_trade_flows(
    timeframe: str = Query("1Y", description="Lookback window: 1W, 1M, 3M, 6M, 1Y, 3Y, ALL"),
    importer: Optional[str] = Query(None, description="Filter by importing country/region"),
    coal_type: Optional[str] = Query(None, description="Filter by coal type"),
):
    """Return US coal export trade flow data."""
    db = _get_db()
    days = _timeframe_to_days(timeframe)

    where_clauses = [
        "period_date >= date('now', :offset)",
        "exporter = 'US'",
    ]
    params: dict = {"offset": f"-{days} days"}

    if importer:
        where_clauses.append("importer = :importer")
        params["importer"] = importer
    if coal_type:
        where_clauses.append("coal_type = :coal_type")
        params["coal_type"] = coal_type

    where_sql = " AND ".join(where_clauses)

    async with db.session_factory() as session:
        result = await session.execute(
            text(f"""
                SELECT exporter, importer, coal_type,
                       volume_mt, value_usd, period_date, source
                FROM trade_flows
                WHERE {where_sql}
                ORDER BY period_date DESC
            """),
            params,
        )
        rows = [
            {
                "exporter": r[0],
                "importer": r[1],
                "coal_type": r[2],
                "volume_mt": r[3],
                "value_usd": r[4],
                "period_date": r[5],
                "source": r[6],
            }
            for r in result.fetchall()
        ]

    return {"timeframe": timeframe, "count": len(rows), "data": rows}


# ------------------------------------------------------------------ #
#  GET /map-data  --  aggregated for map visualization
# ------------------------------------------------------------------ #
@router.get("/map-data")
async def get_map_data(
    timeframe: str = Query("1Y", description="Lookback window"),
):
    """Return trade flow data aggregated by destination for map visualization.

    Groups exports by importer (destination country) and sums volumes,
    providing a dataset suitable for choropleth or flow map rendering.
    """
    db = _get_db()
    days = _timeframe_to_days(timeframe)

    async with db.session_factory() as session:
        result = await session.execute(
            text("""
                SELECT
                    importer,
                    SUM(volume_mt) as total_volume_mt,
                    SUM(value_usd) as total_value_usd,
                    COUNT(*) as record_count,
                    MAX(period_date) as latest_period
                FROM trade_flows
                WHERE period_date >= date('now', :offset)
                  AND exporter = 'US'
                GROUP BY importer
                ORDER BY total_volume_mt DESC
            """),
            {"offset": f"-{days} days"},
        )
        rows = [
            {
                "destination": r[0],
                "total_volume_mt": round(r[1], 4) if r[1] else 0,
                "total_value_usd": round(r[2], 2) if r[2] else None,
                "record_count": r[3],
                "latest_period": r[4],
            }
            for r in result.fetchall()
        ]

    return {"timeframe": timeframe, "destinations": rows}


# ------------------------------------------------------------------ #
#  GET /summary  --  latest trade flow snapshot
# ------------------------------------------------------------------ #
@router.get("/summary")
async def get_summary():
    """Return a summary of recent US coal trade flow activity."""
    db = _get_db()

    async with db.session_factory() as session:
        # Latest quarter's total exports
        latest_result = await session.execute(text("""
            SELECT
                MAX(period_date) as latest_period,
                SUM(volume_mt) as total_volume_mt,
                SUM(value_usd) as total_value_usd,
                COUNT(DISTINCT importer) as destination_count
            FROM trade_flows
            WHERE exporter = 'US'
              AND period_date = (
                  SELECT MAX(period_date) FROM trade_flows WHERE exporter = 'US'
              )
        """))
        latest = latest_result.fetchone()

        # Top 5 destinations in most recent period
        top_dest_result = await session.execute(text("""
            SELECT importer, SUM(volume_mt) as volume_mt
            FROM trade_flows
            WHERE exporter = 'US'
              AND period_date = (
                  SELECT MAX(period_date) FROM trade_flows WHERE exporter = 'US'
              )
            GROUP BY importer
            ORDER BY volume_mt DESC
            LIMIT 5
        """))
        top_destinations = [
            {"destination": r[0], "volume_mt": round(r[1], 4) if r[1] else 0}
            for r in top_dest_result.fetchall()
        ]

        # Quarter-over-quarter trend (compare last two periods)
        trend_result = await session.execute(text("""
            SELECT period_date, SUM(volume_mt) as total_volume
            FROM trade_flows
            WHERE exporter = 'US'
            GROUP BY period_date
            ORDER BY period_date DESC
            LIMIT 2
        """))
        trend_rows = trend_result.fetchall()

    qoq_change_pct = None
    if len(trend_rows) == 2:
        current_vol = trend_rows[0][1] or 0
        prev_vol = trend_rows[1][1] or 0
        if prev_vol > 0:
            qoq_change_pct = round(
                ((current_vol - prev_vol) / prev_vol) * 100, 2
            )

    return {
        "latest_period": latest[0] if latest else None,
        "total_volume_mt": round(latest[1], 4) if latest and latest[1] else None,
        "total_value_usd": round(latest[2], 2) if latest and latest[2] else None,
        "destination_count": latest[3] if latest else 0,
        "top_destinations": top_destinations,
        "qoq_change_pct": qoq_change_pct,
    }
