from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.dependencies import AdminUser, CurrentUser, DB
from app.schemas.telegram import TelegramConfigOut, TelegramConfigRequest
from app.services.telegram_service import (
    broadcast_alert, get_telegram_config, save_telegram_config,
    send_alert_to_user, send_daily_summary,
)


class AlertRequest(BaseModel):
    user_pin: str | None = None
    message: str
    broadcast: bool = False

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


class TestMessageRequest(BaseModel):
    message: str = "🔔 Test alert from NSE Stock Scout!"


@router.post("/test")
async def test_message(
    db: DB, _user: CurrentUser,
    user_pin: str = Query(...),
    body: TestMessageRequest | None = None,
):
    text = body.message if body and body.message else "🔔 Test alert from NSE Stock Scout!"
    success = await send_alert_to_user(db, user_pin, text)
    return {"sent": success}


@router.post("/daily-summary")
async def trigger_daily_summary(db: DB, _user: AdminUser):
    sent = await send_daily_summary(db)
    return {"summaries_sent": sent}


@router.post("/alert/trade")
async def send_trade_alert(req: AlertRequest, db: DB, _user: CurrentUser):
    """Send trade confirmation alert via Telegram."""
    if req.broadcast:
        sent = await broadcast_alert(db, f"<b>Trade Alert</b>\n{req.message}")
        return {"sent_to": sent}
    if not req.user_pin:
        raise HTTPException(400, "user_pin required when not broadcasting")
    ok = await send_alert_to_user(db, req.user_pin, f"<b>Trade Alert</b>\n{req.message}")
    return {"sent": ok}


@router.post("/alert/scanner")
async def send_scanner_alert(req: AlertRequest, db: DB, _user: CurrentUser):
    """Send scanner result alert via Telegram."""
    if req.broadcast:
        sent = await broadcast_alert(db, f"<b>Scanner Alert</b>\n{req.message}")
        return {"sent_to": sent}
    if not req.user_pin:
        raise HTTPException(400, "user_pin required when not broadcasting")
    ok = await send_alert_to_user(db, req.user_pin, f"<b>Scanner Alert</b>\n{req.message}")
    return {"sent": ok}


@router.post("/alert/action")
async def send_action_alert(req: AlertRequest, db: DB, _user: CurrentUser):
    """Send action item alert via Telegram."""
    if req.broadcast:
        sent = await broadcast_alert(db, f"<b>Action Required</b>\n{req.message}")
        return {"sent_to": sent}
    if not req.user_pin:
        raise HTTPException(400, "user_pin required when not broadcasting")
    ok = await send_alert_to_user(db, req.user_pin, f"<b>Action Required</b>\n{req.message}")
    return {"sent": ok}
