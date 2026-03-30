"""
Pricing domain API routes.

Mounted at /api/pricing by main.py.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import text

router = APIRouter()


def _get_db():
    """Lazy import to avoid circular dependency at module load time."""
    from main import _db
    return _db


# ------------------------------------------------------------------ #
#  GET /benchmarks  --  coal price time-series
# ------------------------------------------------------------------ #
@router.get("/benchmarks")
async def get_benchmarks(
    timeframe: str = Query("3M", description="Lookback window: 1W, 1M, 3M, 6M, 1Y, 3Y, ALL"),
    benchmark: str | None = Query(None, description="Filter by benchmark name"),
):
    """Return coal price time-series for all (or one) benchmark(s)."""
    db = _get_db()
    days = _timeframe_to_days(timeframe)

    params: dict = {"offset": f"-{days} days"}
    where = "WHERE timestamp >= datetime('now', :offset)"
    if benchmark:
        where += " AND benchmark = :benchmark"
        params["benchmark"] = benchmark

    async with db.session_factory() as session:
        result = await session.execute(
            text(f"""
                SELECT benchmark, price_usd, currency, timestamp, source
                FROM coal_prices
                {where}
                ORDER BY timestamp ASC
            """),
            params,
        )
        rows = [
            {
                "benchmark": r[0],
                "price_usd": r[1],
                "currency": r[2],
                "timestamp": r[3],
                "source": r[4],
            }
            for r in result.fetchall()
        ]

    return {"timeframe": timeframe, "count": len(rows), "data": rows}


# ------------------------------------------------------------------ #
#  GET /latest  --  most recent value per benchmark
# ------------------------------------------------------------------ #
@router.get("/latest")
async def get_latest():
    """Return the latest price for each coal benchmark and gas benchmark."""
    db = _get_db()

    async with db.session_factory() as session:
        # Latest coal prices
        result = await session.execute(text("""
            SELECT benchmark, price_usd, currency, timestamp, source
            FROM coal_prices
            WHERE id IN (SELECT MAX(id) FROM coal_prices GROUP BY benchmark)
        """))
        coal = [
            {
                "benchmark": r[0],
                "price_usd": r[1],
                "currency": r[2],
                "timestamp": r[3],
                "source": r[4],
            }
            for r in result.fetchall()
        ]

        # Latest gas prices
        result = await session.execute(text("""
            SELECT benchmark, price, unit, timestamp, source
            FROM gas_prices
            WHERE id IN (SELECT MAX(id) FROM gas_prices GROUP BY benchmark)
        """))
        gas = [
            {
                "benchmark": r[0],
                "price": r[1],
                "unit": r[2],
                "timestamp": r[3],
                "source": r[4],
            }
            for r in result.fetchall()
        ]

        # Latest spreads
        result = await session.execute(text("""
            SELECT spread_name, value, timestamp
            FROM price_spreads
            WHERE id IN (SELECT MAX(id) FROM price_spreads GROUP BY spread_name)
        """))
        spreads = [
            {"spread_name": r[0], "value": r[1], "timestamp": r[2]}
            for r in result.fetchall()
        ]

    return {"coal": coal, "gas": gas, "spreads": spreads}


# ------------------------------------------------------------------ #
#  GET /spreads  --  spread time-series
# ------------------------------------------------------------------ #
@router.get("/spreads")
async def get_spreads(
    timeframe: str = Query("6M", description="Lookback window"),
    spread_name: str | None = Query(None, description="Filter by spread name"),
):
    """Return price spread time-series (e.g., gas/coal switching ratio)."""
    db = _get_db()
    days = _timeframe_to_days(timeframe)

    params: dict = {"offset": f"-{days} days"}
    where = "WHERE timestamp >= datetime('now', :offset)"
    if spread_name:
        where += " AND spread_name = :spread_name"
        params["spread_name"] = spread_name

    async with db.session_factory() as session:
        result = await session.execute(
            text(f"""
                SELECT spread_name, value, timestamp
                FROM price_spreads
                {where}
                ORDER BY timestamp ASC
            """),
            params,
        )
        rows = [
            {"spread_name": r[0], "value": r[1], "timestamp": r[2]}
            for r in result.fetchall()
        ]

    return {"timeframe": timeframe, "count": len(rows), "data": rows}


# ------------------------------------------------------------------ #
#  GET /gas  --  Henry Hub time-series
# ------------------------------------------------------------------ #
@router.get("/gas")
async def get_gas(
    timeframe: str = Query("1Y", description="Lookback window"),
    benchmark: str | None = Query(None, description="Gas benchmark (default: all)"),
):
    """Return natural gas price time-series."""
    db = _get_db()
    days = _timeframe_to_days(timeframe)

    params: dict = {"offset": f"-{days} days"}
    where = "WHERE timestamp >= datetime('now', :offset)"
    if benchmark:
        where += " AND benchmark = :benchmark"
        params["benchmark"] = benchmark

    async with db.session_factory() as session:
        result = await session.execute(
            text(f"""
                SELECT benchmark, price, unit, timestamp, source
                FROM gas_prices
                {where}
                ORDER BY timestamp ASC
            """),
            params,
        )
        rows = [
            {
                "benchmark": r[0],
                "price": r[1],
                "unit": r[2],
                "timestamp": r[3],
                "source": r[4],
            }
            for r in result.fetchall()
        ]

    return {"timeframe": timeframe, "count": len(rows), "data": rows}


# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #
def _timeframe_to_days(timeframe: str) -> int:
    mapping = {
        "1W": 7, "1M": 30, "3M": 90, "6M": 180,
        "1Y": 365, "3Y": 1095, "ALL": 36500,
    }
    return mapping.get(timeframe, 365)
