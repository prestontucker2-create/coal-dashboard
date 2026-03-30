import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import text

logger = logging.getLogger(__name__)


SIGNAL_DEFINITIONS = [
    {
        "name": "Newcastle vs 200-DMA",
        "domain": "pricing",
        "query_current": "SELECT price_usd FROM coal_prices WHERE benchmark = 'newcastle' ORDER BY timestamp DESC LIMIT 1",
        "query_context": "SELECT AVG(price_usd) FROM (SELECT price_usd FROM coal_prices WHERE benchmark = 'newcastle' ORDER BY timestamp DESC LIMIT 200)",
        "evaluate": lambda current, context: ("bull", 0.7, "Price above 200-day average") if current and context and current > context
                    else ("bear", 0.6, "Price below 200-day average") if current and context
                    else ("neutral", 0.0, "Insufficient data"),
    },
    {
        "name": "Gas/Coal Switching",
        "domain": "pricing",
        "query_current": "SELECT value FROM price_spreads WHERE spread_name = 'gas_coal_ratio' ORDER BY timestamp DESC LIMIT 1",
        "query_context": None,
        "evaluate": lambda current, _: ("bull", 0.8, "Gas expensive vs coal, switching favors coal") if current and current > 2.5
                    else ("bear", 0.6, "Gas cheap vs coal, switching away from coal") if current and current < 1.5
                    else ("neutral", 0.3, "Gas/coal ratio in neutral zone"),
    },
    {
        "name": "US Inventory Trend",
        "domain": "supply",
        "query_current": "SELECT inventory_tons FROM coal_inventories WHERE location = 'us_electric_power' ORDER BY period_date DESC LIMIT 1",
        "query_context": "SELECT AVG(inventory_tons) FROM coal_inventories WHERE location = 'us_electric_power' AND period_date > date('now', '-5 years')",
        "evaluate": lambda current, avg: ("bull", 0.7, "Inventories below 5-year average") if current and avg and current < avg
                    else ("bear", 0.5, "Inventories above 5-year average") if current and avg
                    else ("neutral", 0.0, "No inventory data"),
    },
    {
        "name": "US Production Trend",
        "domain": "supply",
        "query_current": "SELECT production_tons FROM us_coal_production WHERE region = 'total' ORDER BY period_date DESC LIMIT 1",
        "query_context": "SELECT production_tons FROM us_coal_production WHERE region = 'total' ORDER BY period_date DESC LIMIT 1 OFFSET 12",
        "evaluate": lambda current, year_ago: ("bull", 0.6, "Production declining YoY — supply tightening")
                    if current and year_ago and current < year_ago * 0.98
                    else ("bear", 0.4, "Production growing YoY") if current and year_ago and current > year_ago * 1.02
                    else ("neutral", 0.2, "Production stable"),
    },
    {
        "name": "Coal Gen Share",
        "domain": "demand",
        "query_current": """SELECT g_coal.generation_mwh * 1.0 / g_all.generation_mwh
            FROM power_generation g_coal, power_generation g_all
            WHERE g_coal.region = 'us' AND g_coal.fuel_type = 'coal'
            AND g_all.region = 'us' AND g_all.fuel_type = 'total'
            AND g_coal.period_date = g_all.period_date
            ORDER BY g_coal.period_date DESC LIMIT 1""",
        "query_context": """SELECT g_coal.generation_mwh * 1.0 / g_all.generation_mwh
            FROM power_generation g_coal, power_generation g_all
            WHERE g_coal.region = 'us' AND g_coal.fuel_type = 'coal'
            AND g_all.region = 'us' AND g_all.fuel_type = 'total'
            AND g_coal.period_date = g_all.period_date
            ORDER BY g_coal.period_date DESC LIMIT 1 OFFSET 1""",
        "evaluate": lambda current, prev: ("bull", 0.5, "Coal share of generation rising")
                    if current and prev and current > prev
                    else ("bear", 0.4, "Coal share declining") if current and prev
                    else ("neutral", 0.0, "No generation data"),
    },
    {
        "name": "AUD/USD Trend",
        "domain": "macro",
        "query_current": "SELECT value FROM macro_indicators WHERE indicator = 'audusd' ORDER BY timestamp DESC LIMIT 1",
        "query_context": "SELECT value FROM macro_indicators WHERE indicator = 'audusd' ORDER BY timestamp DESC LIMIT 1 OFFSET 20",
        "evaluate": lambda current, month_ago: ("bull", 0.7, "AUD weakening — boosts WHC margins")
                    if current and month_ago and current < month_ago * 0.98
                    else ("bear", 0.4, "AUD strengthening — compresses WHC margins")
                    if current and month_ago and current > month_ago * 1.02
                    else ("neutral", 0.2, "AUD stable"),
    },
    {
        "name": "Dollar Strength",
        "domain": "macro",
        "query_current": "SELECT value FROM macro_indicators WHERE indicator = 'dxy' ORDER BY timestamp DESC LIMIT 1",
        "query_context": "SELECT value FROM macro_indicators WHERE indicator = 'dxy' ORDER BY timestamp DESC LIMIT 1 OFFSET 20",
        "evaluate": lambda current, month_ago: ("bear", 0.5, "Strong dollar headwind for commodities")
                    if current and month_ago and current > month_ago * 1.02
                    else ("bull", 0.4, "Weak dollar tailwind for commodities")
                    if current and month_ago and current < month_ago * 0.98
                    else ("neutral", 0.2, "Dollar stable"),
    },
    {
        "name": "Insider Activity",
        "domain": "company",
        "query_current": """SELECT SUM(CASE WHEN transaction_type = 'P' THEN total_value ELSE 0 END) -
                           SUM(CASE WHEN transaction_type = 'S' THEN total_value ELSE 0 END)
                    FROM insider_transactions
                    WHERE transaction_date > date('now', '-30 days')""",
        "query_context": None,
        "evaluate": lambda net, _: ("bull", 0.8, "Net insider buying in last 30 days")
                    if net and net > 50000
                    else ("bear", 0.5, "Net insider selling in last 30 days")
                    if net and net < -50000
                    else ("neutral", 0.2, "Minimal insider activity"),
    },
    {
        "name": "ENSO Phase",
        "domain": "weather",
        "query_current": "SELECT phase FROM enso_status ORDER BY period_date DESC LIMIT 1",
        "query_context": None,
        "evaluate": lambda phase, _: ("bull", 0.6, "La Nina — Australian supply disruption risk")
                    if phase == "la_nina"
                    else ("neutral", 0.2, f"ENSO phase: {phase}" if phase else "No ENSO data"),
    },
    {
        "name": "News Sentiment",
        "domain": "sentiment",
        "query_current": "SELECT AVG(sentiment_score) FROM news_headlines WHERE published_at > datetime('now', '-7 days')",
        "query_context": None,
        "evaluate": lambda score, _: ("bull", 0.5, "Positive news sentiment (7d)")
                    if score and score > 0.15
                    else ("bear", 0.5, "Negative news sentiment (7d)")
                    if score and score < -0.15
                    else ("neutral", 0.2, "Neutral news sentiment"),
    },
    {
        "name": "Heating Demand",
        "domain": "weather",
        "query_current": "SELECT hdd, deviation_from_normal FROM degree_days WHERE region = 'us_national' ORDER BY period_date DESC LIMIT 1",
        "query_context": None,
        "evaluate": lambda row, _: ("bull", 0.5, "Colder than normal — elevated heating demand")
                    if row and isinstance(row, (tuple, list)) and len(row) > 1 and row[1] and row[1] > 5
                    else ("neutral", 0.2, "Normal heating demand"),
    },
]


class SignalEngine:
    def __init__(self, db):
        self.db = db

    async def compute_all(self):
        async with self.db.session_factory() as session:
            for sig_def in SIGNAL_DEFINITIONS:
                try:
                    await self._compute_one(session, sig_def)
                except Exception as e:
                    logger.error(f"Signal computation error for '{sig_def['name']}': {e}")

    async def _compute_one(self, session, sig_def):
        # Get current value
        result = await session.execute(text(sig_def["query_current"]))
        row = result.fetchone()
        current = row[0] if row else None

        # Handle multi-column queries (like degree_days)
        if row and len(row) > 1:
            current = tuple(row)

        # Get context value if applicable
        context = None
        if sig_def["query_context"]:
            result = await session.execute(text(sig_def["query_context"]))
            ctx_row = result.fetchone()
            context = ctx_row[0] if ctx_row else None

        # Evaluate
        direction, strength, reasoning = sig_def["evaluate"](current, context)

        # Upsert signal
        async with self.db.session_factory() as write_session:
            async with write_session.begin():
                await write_session.execute(text("""
                    INSERT OR REPLACE INTO signal_board (signal_name, direction, strength, reasoning, domain, updated_at)
                    VALUES (:name, :dir, :str, :reason, :domain, :updated)
                """), {
                    "name": sig_def["name"],
                    "dir": direction,
                    "str": strength,
                    "reason": reasoning,
                    "domain": sig_def["domain"],
                    "updated": datetime.now(timezone.utc).isoformat(),
                })

        logger.debug(f"Signal '{sig_def['name']}': {direction} ({strength:.1f}) — {reasoning}")
