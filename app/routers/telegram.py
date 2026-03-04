from fastapi import APIRouter, HTTPException, Query

from app.dependencies import AdminUser, CurrentUser, DB
from app.schemas.telegram import TelegramConfigOut, TelegramConfigRequest
from app.services.telegram_service import (
    get_telegram_config, save_telegram_config, send_alert_to_user, send_daily_summary,
)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.get("/config", response_model=TelegramConfigOut)
def get_config(db: DB, _user: CurrentUser, user_pin: str = Query(...)):
    config = get_telegram_config(db, user_pin)
    if not config:
        raise HTTPException(status_code=404, detail="Telegram not configured")
    return config


@router.post("/config", response_model=TelegramConfigOut)
def save_config(req: TelegramConfigRequest, db: DB, _user: CurrentUser):
    config = save_telegram_config(db, req.user_pin, req.bot_token, req.chat_id, req.enabled)
    return config


@router.post("/test")
async def test_message(db: DB, _user: CurrentUser, user_pin: str = Query(...)):
    success = await send_alert_to_user(db, user_pin, "🔔 Test alert from NSE Stock Scout!")
    return {"sent": success}


@router.post("/daily-summary")
async def trigger_daily_summary(db: DB, _user: AdminUser):
    sent = await send_daily_summary(db)
    return {"summaries_sent": sent}
