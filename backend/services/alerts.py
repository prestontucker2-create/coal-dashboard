import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
import httpx

logger = logging.getLogger(__name__)

CONDITION_OPS = {
    "gt": lambda val, thresh: val > thresh,
    "lt": lambda val, thresh: val < thresh,
    "gte": lambda val, thresh: val >= thresh,
    "lte": lambda val, thresh: val <= thresh,
    "pct_change_gt": None,  # Handled separately
    "pct_change_lt": None,
}

# Maps domain+metric to SQL query for current value
METRIC_QUERIES = {
    ("pricing", "newcastle"): "SELECT price_usd FROM coal_prices WHERE benchmark = 'newcastle' ORDER BY timestamp DESC LIMIT 1",
    ("pricing", "henry_hub"): "SELECT price FROM gas_prices WHERE benchmark = 'henry_hub' ORDER BY timestamp DESC LIMIT 1",
    ("pricing", "gas_coal_ratio"): "SELECT value FROM price_spreads WHERE spread_name = 'gas_coal_ratio' ORDER BY timestamp DESC LIMIT 1",
    ("macro", "audusd"): "SELECT value FROM macro_indicators WHERE indicator = 'audusd' ORDER BY timestamp DESC LIMIT 1",
    ("macro", "dxy"): "SELECT value FROM macro_indicators WHERE indicator = 'dxy' ORDER BY timestamp DESC LIMIT 1",
    ("macro", "us10y"): "SELECT value FROM macro_indicators WHERE indicator = 'us10y' ORDER BY timestamp DESC LIMIT 1",
    ("company", "btu_price"): "SELECT close FROM stock_prices WHERE ticker = 'BTU' ORDER BY date DESC LIMIT 1",
    ("company", "whc_price"): "SELECT close FROM stock_prices WHERE ticker = 'WHC.AX' ORDER BY date DESC LIMIT 1",
}


class AlertEngine:
    def __init__(self, db, config):
        self.db = db
        self.config = config

    async def evaluate_all(self):
        if not self.config.alerts.enabled:
            return

        async with self.db.session_factory() as session:
            result = await session.execute(text(
                "SELECT id, name, domain, metric, condition, threshold, timeframe_minutes, channels "
                "FROM alert_configs WHERE is_active = 1"
            ))
            configs = result.fetchall()

        for cfg in configs:
            alert_id, name, domain, metric, condition, threshold, tf_min, channels = cfg
            try:
                await self._evaluate_one(alert_id, name, domain, metric, condition, threshold, tf_min, channels)
            except Exception as e:
                logger.error(f"Alert evaluation error for '{name}': {e}")

    async def _evaluate_one(self, alert_id, name, domain, metric, condition, threshold, tf_min, channels):
        query_key = (domain, metric)
        query = METRIC_QUERIES.get(query_key)
        if not query:
            # Try generic stock price query
            if domain == "company" and metric.endswith("_price"):
                ticker = metric.replace("_price", "").upper()
                query = f"SELECT close FROM stock_prices WHERE ticker = '{ticker}' ORDER BY date DESC LIMIT 1"
            else:
                return

        async with self.db.session_factory() as session:
            result = await session.execute(text(query))
            row = result.fetchone()
            if not row:
                return
            current_value = row[0]

            if condition in ("pct_change_gt", "pct_change_lt"):
                # Get value from timeframe_minutes ago
                cutoff = (datetime.now(timezone.utc) - timedelta(minutes=tf_min)).isoformat()
                # Use same query pattern but with time filter
                old_query = query.replace("ORDER BY", f"AND timestamp < '{cutoff}' ORDER BY").replace("LIMIT 1", "LIMIT 1")
                if "timestamp" not in old_query:
                    old_query = query.replace("ORDER BY", f"AND date < '{cutoff[:10]}' ORDER BY")
                result = await session.execute(text(old_query))
                old_row = result.fetchone()
                if not old_row or not old_row[0]:
                    return
                pct_change = ((current_value - old_row[0]) / old_row[0]) * 100
                triggered = (condition == "pct_change_gt" and pct_change > threshold) or \
                           (condition == "pct_change_lt" and pct_change < threshold)
                eval_value = pct_change
            else:
                op = CONDITION_OPS.get(condition)
                if not op:
                    return
                triggered = op(current_value, threshold)
                eval_value = current_value

            if not triggered:
                return

            # Check cooldown
            cooldown_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=self.config.alerts.cooldown_minutes)).isoformat()
            result = await session.execute(text(
                "SELECT id FROM alert_history WHERE alert_config_id = :id AND triggered_at > :cutoff"
            ), {"id": alert_id, "cutoff": cooldown_cutoff})
            if result.fetchone():
                return  # Still in cooldown

        # Trigger alert
        message = f"[{name}] {metric} = {eval_value:.4f} (threshold: {condition} {threshold})"
        logger.info(f"ALERT TRIGGERED: {message}")

        # Store in history
        async with self.db.session_factory() as session:
            async with session.begin():
                await session.execute(text(
                    "INSERT INTO alert_history (alert_config_id, triggered_value, message, dispatched_via) "
                    "VALUES (:id, :val, :msg, :via)"
                ), {"id": alert_id, "val": eval_value, "msg": message, "via": channels})

        # Dispatch
        if "telegram" in channels:
            await self._dispatch_telegram(message)

    async def _dispatch_telegram(self, message: str):
        token = self.config.api_keys.telegram_bot_token
        chat_id = self.config.api_keys.telegram_chat_id
        if not token or not chat_id:
            logger.warning("Telegram not configured, skipping dispatch")
            return

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json={
                    "chat_id": chat_id,
                    "text": f"🔔 Coal Dashboard Alert\n\n{message}",
                    "parse_mode": "HTML",
                })
                if resp.status_code != 200:
                    logger.error(f"Telegram dispatch failed: {resp.text}")
        except Exception as e:
            logger.error(f"Telegram dispatch error: {e}")
