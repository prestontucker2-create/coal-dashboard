from fastapi import APIRouter
from sqlalchemy import text

router = APIRouter()


@router.get("/overview")
async def get_overview():
    from main import _db

    async with _db.session_factory() as session:
        # Key prices - latest coal benchmarks
        result = await session.execute(text("""
            SELECT benchmark, price_usd, timestamp, source
            FROM coal_prices
            WHERE id IN (
                SELECT MAX(id) FROM coal_prices GROUP BY benchmark
            )
        """))
        coal_prices = [
            {"benchmark": r[0], "price": r[1], "timestamp": r[2], "source": r[3]}
            for r in result.fetchall()
        ]

        # Gas prices
        result = await session.execute(text("""
            SELECT benchmark, price, timestamp
            FROM gas_prices
            WHERE id IN (SELECT MAX(id) FROM gas_prices GROUP BY benchmark)
        """))
        gas_prices = [
            {"benchmark": r[0], "price": r[1], "timestamp": r[2]}
            for r in result.fetchall()
        ]

        # Macro indicators (latest)
        result = await session.execute(text("""
            SELECT indicator, value, timestamp
            FROM macro_indicators
            WHERE id IN (SELECT MAX(id) FROM macro_indicators GROUP BY indicator)
        """))
        macro = [
            {"indicator": r[0], "value": r[1], "timestamp": r[2]}
            for r in result.fetchall()
        ]

        # Watchlist - latest stock prices with change
        result = await session.execute(text("""
            SELECT s1.ticker, s1.close, s1.volume, s1.date,
                   s2.close as prev_close
            FROM stock_prices s1
            LEFT JOIN stock_prices s2 ON s1.ticker = s2.ticker
                AND s2.date = (SELECT MAX(date) FROM stock_prices WHERE ticker = s1.ticker AND date < s1.date)
            WHERE s1.date = (SELECT MAX(date) FROM stock_prices WHERE ticker = s1.ticker)
            ORDER BY s1.ticker
        """))
        watchlist = []
        for r in result.fetchall():
            prev = r[4] if r[4] else r[1]
            change_pct = ((r[1] - prev) / prev * 100) if prev else 0
            watchlist.append({
                "ticker": r[0], "price": r[1], "volume": r[2],
                "date": r[3], "change_pct": round(change_pct, 2),
            })

        # Signal board
        result = await session.execute(text("""
            SELECT signal_name, direction, strength, reasoning, domain, updated_at
            FROM signal_board ORDER BY domain, signal_name
        """))
        signals = [
            {
                "name": r[0], "direction": r[1], "strength": r[2],
                "reasoning": r[3], "domain": r[4], "updated_at": r[5],
            }
            for r in result.fetchall()
        ]

        # Recent alerts
        result = await session.execute(text("""
            SELECT ah.message, ah.triggered_at, ah.dispatched_via,
                   ac.name, ac.domain
            FROM alert_history ah
            LEFT JOIN alert_configs ac ON ah.alert_config_id = ac.id
            ORDER BY ah.triggered_at DESC LIMIT 10
        """))
        alerts = [
            {
                "message": r[0], "triggered_at": r[1], "dispatched_via": r[2],
                "alert_name": r[3], "domain": r[4],
            }
            for r in result.fetchall()
        ]

        # Coal price 30d trend (Newcastle)
        result = await session.execute(text("""
            SELECT timestamp, price_usd FROM coal_prices
            WHERE benchmark = 'newcastle'
            ORDER BY timestamp DESC LIMIT 30
        """))
        coal_trend = [{"date": r[0], "price": r[1]} for r in result.fetchall()]
        coal_trend.reverse()

    return {
        "coal_prices": coal_prices,
        "gas_prices": gas_prices,
        "macro": macro,
        "watchlist": watchlist,
        "signals": signals,
        "recent_alerts": alerts,
        "coal_price_trend": coal_trend,
    }
