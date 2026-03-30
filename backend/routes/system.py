from fastapi import APIRouter, Query
from sqlalchemy import text

router = APIRouter()


@router.get("/health")
async def health():
    from main import _db, _scheduler, _orchestrators
    from services.data_freshness import DataFreshnessMonitor

    scheduler_running = _scheduler.running if _scheduler else False
    monitor = DataFreshnessMonitor(_db)
    summary = await monitor.get_summary()

    return {
        "status": "ok",
        "scheduler_running": scheduler_running,
        "registered_domains": list(_orchestrators.keys()),
        "data_health": summary,
    }


@router.get("/correlation")
async def correlation(timeframe: str = Query("1Y")):
    from main import _db
    from services.correlation import CorrelationService

    svc = CorrelationService(_db)
    return await svc.calculate_matrix(timeframe)


@router.get("/freshness")
async def freshness():
    from main import _db
    async with _db.session_factory() as session:
        result = await session.execute(
            text("SELECT source_name, domain, last_success, last_attempt, last_error, expected_interval_seconds, record_count FROM data_freshness ORDER BY domain, source_name")
        )
        rows = result.fetchall()

    return [
        {
            "source_name": r[0],
            "domain": r[1],
            "last_success": r[2],
            "last_attempt": r[3],
            "last_error": r[4],
            "expected_interval_seconds": r[5],
            "record_count": r[6],
        }
        for r in rows
    ]


@router.post("/refresh/{domain}")
async def manual_refresh(domain: str):
    from main import _orchestrators
    orch = _orchestrators.get(domain)
    if not orch:
        return {"error": f"Domain '{domain}' not found", "available": list(_orchestrators.keys())}
    count = await orch.run()
    return {"domain": domain, "records_updated": count}
