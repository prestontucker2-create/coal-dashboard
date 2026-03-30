import logging
from datetime import datetime, timezone
from sqlalchemy import text

logger = logging.getLogger(__name__)


class DataFreshnessMonitor:
    def __init__(self, db):
        self.db = db

    async def check_all(self) -> list[dict]:
        async with self.db.session_factory() as session:
            result = await session.execute(text("""
                SELECT source_name, domain, last_success, last_attempt,
                       last_error, expected_interval_seconds, record_count
                FROM data_freshness ORDER BY domain, source_name
            """))
            rows = result.fetchall()

        now = datetime.now(timezone.utc)
        statuses = []

        for r in rows:
            source_name, domain, last_success, last_attempt, last_error, expected_interval, record_count = r

            if last_success:
                try:
                    if isinstance(last_success, str):
                        ls = datetime.fromisoformat(last_success.replace("Z", "+00:00"))
                    else:
                        ls = last_success
                    if ls.tzinfo is None:
                        ls = ls.replace(tzinfo=timezone.utc)
                    age_seconds = (now - ls).total_seconds()
                except Exception:
                    age_seconds = float("inf")
            else:
                age_seconds = float("inf")

            if expected_interval and expected_interval > 0:
                ratio = age_seconds / expected_interval
                if ratio <= 1.5:
                    status = "fresh"
                elif ratio <= 3.0:
                    status = "stale"
                else:
                    status = "error"
            elif last_error:
                status = "error"
            elif last_success:
                status = "fresh"
            else:
                status = "unknown"

            statuses.append({
                "source_name": source_name,
                "domain": domain,
                "last_success": last_success,
                "last_attempt": last_attempt,
                "last_error": last_error,
                "expected_interval_seconds": expected_interval,
                "record_count": record_count,
                "age_seconds": round(age_seconds, 0) if age_seconds != float("inf") else None,
                "status": status,
            })

        return statuses

    async def get_summary(self) -> dict:
        statuses = await self.check_all()
        fresh = sum(1 for s in statuses if s["status"] == "fresh")
        stale = sum(1 for s in statuses if s["status"] == "stale")
        error = sum(1 for s in statuses if s["status"] == "error")
        unknown = sum(1 for s in statuses if s["status"] == "unknown")

        return {
            "total_sources": len(statuses),
            "fresh": fresh,
            "stale": stale,
            "error": error,
            "unknown": unknown,
            "overall": "healthy" if error == 0 and stale == 0 else "degraded" if error == 0 else "unhealthy",
        }
