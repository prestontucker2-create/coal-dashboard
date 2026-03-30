"""
Weather domain API routes.

Mounted at /api/weather by main.py.
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
        "1W": 7, "1M": 30, "3M": 90, "6M": 180,
        "1Y": 365, "3Y": 1095, "ALL": 36500,
    }
    return mapping.get(timeframe, 365)


# ------------------------------------------------------------------ #
#  GET /degree-days  --  HDD/CDD time-series
# ------------------------------------------------------------------ #
@router.get("/degree-days")
async def get_degree_days(
    timeframe: str = Query("6M", description="Lookback window: 1W, 1M, 3M, 6M, 1Y, 3Y, ALL"),
):
    """Return heating and cooling degree day time-series."""
    db = _get_db()
    days = _timeframe_to_days(timeframe)

    async with db.session_factory() as session:
        result = await session.execute(
            text("""
                SELECT region, hdd, cdd, deviation_from_normal,
                       period_date, source
                FROM degree_days
                WHERE period_date >= date('now', :offset)
                ORDER BY period_date ASC
            """),
            {"offset": f"-{days} days"},
        )
        rows = [
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

    return {"timeframe": timeframe, "count": len(rows), "data": rows}


# ------------------------------------------------------------------ #
#  GET /enso  --  current ENSO status
# ------------------------------------------------------------------ #
@router.get("/enso")
async def get_enso():
    """Return current ENSO status and recent ONI history."""
    db = _get_db()

    async with db.session_factory() as session:
        # Latest ENSO record
        latest_result = await session.execute(text("""
            SELECT oni_value, phase, period_date, source
            FROM enso_status
            ORDER BY period_date DESC
            LIMIT 1
        """))
        latest = latest_result.fetchone()

        # Last 12 months for trend context
        history_result = await session.execute(text("""
            SELECT oni_value, phase, period_date, source
            FROM enso_status
            WHERE period_date >= date('now', '-365 days')
            ORDER BY period_date ASC
        """))
        history = [
            {
                "oni_value": r[0],
                "phase": r[1],
                "period_date": r[2],
                "source": r[3],
            }
            for r in history_result.fetchall()
        ]

    current = None
    if latest:
        current = {
            "oni_value": latest[0],
            "phase": latest[1],
            "period_date": latest[2],
            "source": latest[3],
        }

    return {"current": current, "history": history}


# ------------------------------------------------------------------ #
#  GET /summary  --  combined weather snapshot
# ------------------------------------------------------------------ #
@router.get("/summary")
async def get_summary():
    """Return a combined weather snapshot: latest ENSO + recent degree day totals."""
    db = _get_db()

    async with db.session_factory() as session:
        # Latest ENSO
        enso_result = await session.execute(text("""
            SELECT oni_value, phase, period_date
            FROM enso_status
            ORDER BY period_date DESC
            LIMIT 1
        """))
        enso_row = enso_result.fetchone()

        # Recent degree days -- aggregate last 4 weeks
        dd_result = await session.execute(text("""
            SELECT
                region,
                AVG(hdd) as avg_hdd,
                AVG(cdd) as avg_cdd,
                AVG(deviation_from_normal) as avg_deviation,
                MAX(period_date) as latest_date
            FROM degree_days
            WHERE period_date >= date('now', '-28 days')
            GROUP BY region
            ORDER BY region
        """))
        dd_rows = dd_result.fetchall()

    enso = None
    if enso_row:
        enso = {
            "oni_value": enso_row[0],
            "phase": enso_row[1],
            "period_date": enso_row[2],
        }

    degree_days_summary = [
        {
            "region": r[0],
            "avg_hdd": round(r[1], 1) if r[1] is not None else None,
            "avg_cdd": round(r[2], 1) if r[2] is not None else None,
            "avg_deviation": round(r[3], 1) if r[3] is not None else None,
            "latest_date": r[4],
        }
        for r in dd_rows
    ]

    return {
        "enso": enso,
        "degree_days": degree_days_summary,
    }
