"""Kite Connect integration — OAuth, portfolio, positions, margins, orders."""
import logging
from datetime import datetime, timezone

from kiteconnect import KiteConnect
from supabase import Client

from app.config import settings
from app.services.activity import log_activity

logger = logging.getLogger(__name__)


def _get_kite_account(db: Client, user_pin: str) -> dict:
    result = db.table("user_kite_accounts").select("*").eq("user_pin", user_pin).limit(1).execute()
    if not result.data:
        raise ValueError(f"No Kite account for user_pin={user_pin}")
    return result.data[0]


def _get_kite_client(db: Client, user_pin: str) -> KiteConnect:
    acct = _get_kite_account(db, user_pin)
    if not acct.get("api_key") or not acct.get("access_token"):
        raise ValueError("Kite credentials incomplete — re-authenticate")
    kite = KiteConnect(api_key=acct["api_key"])
    kite.set_access_token(acct["access_token"])
    return kite


def save_credentials(db: Client, user_pin: str, api_key: str, api_secret: str):
    acct = _get_kite_account(db, user_pin)
    db.table("user_kite_accounts").update({
        "api_key": api_key,
        "api_secret": api_secret,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", acct["id"]).execute()
    return {**acct, "api_key": api_key, "api_secret": api_secret}


def get_login_url(db: Client, user_pin: str) -> str:
    acct = _get_kite_account(db, user_pin)
    if not acct.get("api_key"):
        raise ValueError("API key not configured — save credentials first")
    kite = KiteConnect(api_key=acct["api_key"])
    return kite.login_url()


def handle_callback(db: Client, user_pin: str, request_token: str) -> dict:
    acct = _get_kite_account(db, user_pin)
    kite = KiteConnect(api_key=acct["api_key"])
    data = kite.generate_session(request_token, api_secret=acct["api_secret"])

    result = db.table("user_kite_accounts").update({
        "access_token": data["access_token"],
        "request_token": request_token,
        "is_connected": True,
        "last_login_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", acct["id"]).execute()

    log_activity(db, event_type="kite_login", entity_type="kite", entity_id=user_pin,
                 message=f"Kite connected for {user_pin}", status="completed")
    return result.data[0] if result.data else acct


def get_holdings(db: Client, user_pin: str) -> list[dict]:
    kite = _get_kite_client(db, user_pin)
    holdings = kite.holdings()
    return [
        {
            "tradingsymbol": h["tradingsymbol"],
            "exchange": h.get("exchange", "NSE"),
            "quantity": h["quantity"],
            "average_price": h["average_price"],
            "last_price": h["last_price"],
            "pnl": h["pnl"],
        }
        for h in holdings
    ]


def get_positions(db: Client, user_pin: str) -> list[dict]:
    kite = _get_kite_client(db, user_pin)
    positions = kite.positions()
    result = []
    for p in positions.get("day", []) + positions.get("net", []):
        result.append({
            "tradingsymbol": p["tradingsymbol"],
            "exchange": p.get("exchange", "NSE"),
            "quantity": p["quantity"],
            "average_price": p["average_price"],
            "last_price": p["last_price"],
            "pnl": p["pnl"],
            "product": p.get("product", "CNC"),
        })
    return result


def get_margins(db: Client, user_pin: str) -> dict:
    kite = _get_kite_client(db, user_pin)
    margins = kite.margins()
    equity = margins.get("equity", {})
    return {
        "available_cash": equity.get("available", {}).get("cash", 0),
        "used_margin": equity.get("utilised", {}).get("debits", 0),
        "available_margin": equity.get("net", 0),
    }


def place_order(db: Client, user_pin: str, symbol: str, exchange: str,
                transaction_type: str, quantity: int, order_type: str,
                price: float | None, product: str) -> dict:
    kite = _get_kite_client(db, user_pin)

    order_params = {
        "tradingsymbol": symbol,
        "exchange": exchange,
        "transaction_type": transaction_type,
        "quantity": quantity,
        "order_type": order_type,
        "product": product,
        "variety": "regular",
    }
    if order_type == "LIMIT" and price:
        order_params["price"] = price

    order_id = kite.place_order(**order_params)

    side = "buy" if transaction_type == "BUY" else "sell"
    db.table("user_trades").insert({
        "user_pin": user_pin,
        "symbol": symbol,
        "side": side,
        "qty": quantity,
        "price": price or 0,
        "order_id": str(order_id),
        "status": "placed",
        "notes": f"via Kite {order_type} {product}",
    }).execute()

    log_activity(db, event_type="order_placed", entity_type="trade", entity_id=str(order_id),
                 message=f"{transaction_type} {quantity} {symbol} @ {order_type}",
                 status="completed", metadata_json={"user_pin": user_pin})

    return {"order_id": order_id, "status": "placed"}
