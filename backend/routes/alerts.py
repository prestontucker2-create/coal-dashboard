from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import text

router = APIRouter()


class AlertConfigCreate(BaseModel):
    name: str
    domain: str
    metric: str
    condition: str
    threshold: float
    timeframe_minutes: int = 1440
    channels: str = "telegram"


class AlertConfigUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    threshold: Optional[float] = None
    channels: Optional[str] = None


@router.get("/configs")
async def list_alerts():
    from main import _db
    async with _db.session_factory() as session:
        result = await session.execute(
            text("SELECT id, name, domain, metric, condition, threshold, timeframe_minutes, is_active, channels, created_at FROM alert_configs ORDER BY created_at DESC")
        )
        rows = result.fetchall()

    return [
        {
            "id": r[0], "name": r[1], "domain": r[2], "metric": r[3],
            "condition": r[4], "threshold": r[5], "timeframe_minutes": r[6],
            "is_active": bool(r[7]), "channels": r[8], "created_at": r[9],
        }
        for r in rows
    ]


@router.post("/configs")
async def create_alert(alert: AlertConfigCreate):
    from main import _db
    async with _db.session_factory() as session:
        async with session.begin():
            await session.execute(
                text("""INSERT INTO alert_configs (name, domain, metric, condition, threshold, timeframe_minutes, channels)
                        VALUES (:name, :domain, :metric, :condition, :threshold, :tf, :channels)"""),
                {
                    "name": alert.name, "domain": alert.domain, "metric": alert.metric,
                    "condition": alert.condition, "threshold": alert.threshold,
                    "tf": alert.timeframe_minutes, "channels": alert.channels,
                },
            )
    return {"status": "created"}


@router.put("/configs/{alert_id}")
async def update_alert(alert_id: int, update: AlertConfigUpdate):
    from main import _db
    sets = []
    params = {"id": alert_id}
    if update.name is not None:
        sets.append("name = :name")
        params["name"] = update.name
    if update.is_active is not None:
        sets.append("is_active = :active")
        params["active"] = int(update.is_active)
    if update.threshold is not None:
        sets.append("threshold = :threshold")
        params["threshold"] = update.threshold
    if update.channels is not None:
        sets.append("channels = :channels")
        params["channels"] = update.channels

    if not sets:
        return {"status": "no changes"}

    async with _db.session_factory() as session:
        async with session.begin():
            await session.execute(
                text(f"UPDATE alert_configs SET {', '.join(sets)} WHERE id = :id"),
                params,
            )
    return {"status": "updated"}


@router.delete("/configs/{alert_id}")
async def delete_alert(alert_id: int):
    from main import _db
    async with _db.session_factory() as session:
        async with session.begin():
            await session.execute(
                text("DELETE FROM alert_configs WHERE id = :id"),
                {"id": alert_id},
            )
    return {"status": "deleted"}


@router.get("/history")
async def alert_history(limit: int = 50):
    from main import _db
    async with _db.session_factory() as session:
        result = await session.execute(
            text("""SELECT ah.id, ah.triggered_value, ah.message, ah.dispatched_via, ah.triggered_at,
                           ac.name, ac.domain, ac.metric
                    FROM alert_history ah
                    LEFT JOIN alert_configs ac ON ah.alert_config_id = ac.id
                    ORDER BY ah.triggered_at DESC LIMIT :limit"""),
            {"limit": limit},
        )
        rows = result.fetchall()

    return [
        {
            "id": r[0], "triggered_value": r[1], "message": r[2],
            "dispatched_via": r[3], "triggered_at": r[4],
            "alert_name": r[5], "domain": r[6], "metric": r[7],
        }
        for r in rows
    ]
