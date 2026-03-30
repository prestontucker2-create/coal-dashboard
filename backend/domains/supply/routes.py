"""
Supply domain API routes.

Mounted at ``/api/supply`` by the main FastAPI app.
"""

from fastapi import APIRouter, Query
from sqlalchemy import text

router = APIRouter()


def _get_db():
    """Late import to avoid circular dependency at module load time."""
    from main import _db
    return _db


# ---- GET /production ------------------------------------------------------

@router.get("/production")
async def get_production(
    region: str = Query("total", description="Region / state filter"),
    timeframe: str = Query("1Y", description="Lookback: 1W, 1M, 3M, 6M, 1Y, 3Y, ALL"),
):
    """
    Return US coal production records, optionally filtered by region and
    timeframe.
    """
    db = _get_db()
    days = _timeframe_to_days(timeframe)
    params: dict = {"offset": f"-{days} days"}

    clauses = ["period_date >= date('now', :offset)"]
    if region.lower() != "total":
        clauses.append("LOWER(region) = LOWER(:region)")
        params["region"] = region

    where = " AND ".join(clauses)

    async with db.session_factory() as session:
        result = await session.execute(
            text(f"""
                SELECT region, production_tons, period_type, period_date, source
                FROM us_coal_production
                WHERE {where}
                ORDER BY period_date DESC
            """),
            params,
        )
        rows = result.fetchall()

    return {
        "region": region,
        "timeframe": timeframe,
        "count": len(rows),
        "data": [
            {
                "region": r[0],
                "production_tons": r[1],
                "period_type": r[2],
                "period_date": r[3],
                "source": r[4],
            }
            for r in rows
        ],
    }


# ---- GET /inventories -----------------------------------------------------

@router.get("/inventories")
async def get_inventories(
    timeframe: str = Query("6M", description="Lookback: 1M, 3M, 6M, 1Y, ALL"),
):
    """
    Return coal inventory (stocks) data for the US electric power sector.
    """
    db = _get_db()
    days = _timeframe_to_days(timeframe)

    async with db.session_factory() as session:
        result = await session.execute(
            text("""
                SELECT location, inventory_tons, days_supply, period_date, source
                FROM coal_inventories
                WHERE period_date >= date('now', :offset)
                ORDER BY period_date DESC
            """),
            {"offset": f"-{days} days"},
        )
        rows = result.fetchall()

    return {
        "timeframe": timeframe,
        "count": len(rows),
        "data": [
            {
                "location": r[0],
                "inventory_tons": r[1],
                "days_supply": r[2],
                "period_date": r[3],
                "source": r[4],
            }
            for r in rows
        ],
    }


# ---- GET /summary ---------------------------------------------------------

@router.get("/summary")
async def get_supply_summary():
    """
    Quick snapshot: latest production figure + latest inventory figure.
    Useful for dashboard cards / KPI tiles.
    """
    db = _get_db()

    async with db.session_factory() as session:
        # Latest production row
        prod_result = await session.execute(
            text("""
                SELECT region, production_tons, period_type, period_date
                FROM us_coal_production
                ORDER BY period_date DESC
                LIMIT 1
            """)
        )
        prod_row = prod_result.fetchone()

        # Year-ago production for YoY comparison
        prod_yoy = None
        if prod_row:
            yoy_result = await session.execute(
                text("""
                    SELECT production_tons
                    FROM us_coal_production
                    WHERE region = :region
                      AND period_type = :pt
                      AND period_date <= date(:pd, '-1 year')
                    ORDER BY period_date DESC
                    LIMIT 1
                """),
                {
                    "region": prod_row[0],
                    "pt": prod_row[2],
                    "pd": prod_row[3],
                },
            )
            yoy_row = yoy_result.fetchone()
            if yoy_row and yoy_row[0] and yoy_row[0] > 0:
                prod_yoy = round(
                    (prod_row[1] - yoy_row[0]) / yoy_row[0] * 100, 2
                )

        # Latest inventory row
        inv_result = await session.execute(
            text("""
                SELECT location, inventory_tons, days_supply, period_date
                FROM coal_inventories
                ORDER BY period_date DESC
                LIMIT 1
            """)
        )
        inv_row = inv_result.fetchone()

    production_snapshot = None
    if prod_row:
        production_snapshot = {
            "region": prod_row[0],
            "production_tons": prod_row[1],
            "period_type": prod_row[2],
            "period_date": prod_row[3],
            "yoy_change_pct": prod_yoy,
        }

    inventory_snapshot = None
    if inv_row:
        inventory_snapshot = {
            "location": inv_row[0],
            "inventory_tons": inv_row[1],
            "days_supply": inv_row[2],
            "period_date": inv_row[3],
        }

    return {
        "production": production_snapshot,
        "inventory": inventory_snapshot,
    }


# ---- helpers ---------------------------------------------------------------

def _timeframe_to_days(timeframe: str) -> int:
    mapping = {
        "1W": 7,
        "1M": 30,
        "3M": 90,
        "6M": 180,
        "1Y": 365,
        "3Y": 1095,
        "ALL": 36500,
    }
    return mapping.get(timeframe.upper(), 365)
