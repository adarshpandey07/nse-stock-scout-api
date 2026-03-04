"""Telegram bot service — push alerts for actions, trades, daily summary."""
import logging

import httpx
from supabase import Client

from app.config import settings

logger = logging.getLogger(__name__)


def get_telegram_config(db: Client, user_pin: str) -> dict | None:
    result = db.table("telegram_config").select("*").eq("user_pin", user_pin).limit(1).execute()
    return result.data[0] if result.data else None


def save_telegram_config(db: Client, user_pin: str, bot_token: str,
                         chat_id: str, enabled: bool = True) -> dict:
    existing = db.table("telegram_config").select("id").eq("user_pin", user_pin).limit(1).execute()
    row = {"user_pin": user_pin, "bot_token": bot_token, "chat_id": chat_id, "enabled": enabled}

    if existing.data:
        result = db.table("telegram_config").update(row).eq("user_pin", user_pin).execute()
    else:
        result = db.table("telegram_config").insert(row).execute()

    return result.data[0] if result.data else row


async def send_message(bot_token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={
                "chat_id": chat_id, "text": text, "parse_mode": "HTML",
            })
            return resp.status_code == 200
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


async def send_alert_to_user(db: Client, user_pin: str, message: str) -> bool:
    config = get_telegram_config(db, user_pin)
    if not config or not config.get("enabled"):
        return False
    return await send_message(config["bot_token"], config["chat_id"], message)


async def broadcast_alert(db: Client, message: str) -> int:
    configs = db.table("telegram_config").select("*").eq("enabled", True).execute().data
    sent = 0
    for config in configs:
        if await send_message(config["bot_token"], config["chat_id"], message):
            sent += 1
    return sent


async def send_daily_summary(db: Client) -> int:
    from app.services.dashboard_service import get_dashboard_summary

    configs = db.table("telegram_config").select("*").eq("enabled", True).execute().data
    sent = 0

    for config in configs:
        user_pin = config.get("user_pin")
        if not user_pin:
            continue
        try:
            summary = get_dashboard_summary(db, user_pin)
            portfolio = summary["portfolio"]
            msg = (
                f"<b>Daily Summary</b>\n\n"
                f"<b>Portfolio:</b> {portfolio['total_current']:,.0f} "
                f"({'up' if portfolio['total_pnl'] >= 0 else 'down'} {abs(portfolio['total_pnl']):,.0f})\n"
                f"<b>Wallet:</b> {summary['wallet_balance']:,.0f}\n"
                f"<b>Pending Actions:</b> {summary['pending_actions']}\n"
                f"<b>Scan Hits Today:</b> {summary['latest_scan_results']}\n"
                f"<b>F-Scanner Pass:</b> {summary['f_scanner_summary'].get('all_pass', 0)}\n"
            )
            if await send_message(config["bot_token"], config["chat_id"], msg):
                sent += 1
        except Exception as e:
            logger.error(f"Daily summary failed for {user_pin}: {e}")
    return sent
