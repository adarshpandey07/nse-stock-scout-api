"""Order execution — paper + live mode trading via py-clob-client."""

import logging
from datetime import datetime, timezone

from supabase import Client

from app.config import settings
from app.services.activity import log_activity
from app.services.polymarket.risk_manager import check_limits, get_config

logger = logging.getLogger(__name__)

TAKER_FEE = 0.003  # 0.30%


def _is_paper_mode(db: Client, user_pin: str) -> bool:
    """Check if user is in paper mode (global override or per-user)."""
    if settings.polymarket_paper_mode:
        return True
    config = get_config(db, user_pin)
    return config.get("paper_mode", True)


def _simulate_paper_fill(order_row: dict) -> dict:
    """Paper mode: instant fill at requested price with simulated taker fee."""
    price = float(order_row["price"])
    size = float(order_row["size"])
    fee = round(price * size * TAKER_FEE, 6)

    return {
        "status": "matched",
        "filled_size": size,
        "avg_fill_price": price,
        "fee_paid": fee,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _get_clob_client(db: Client, user_pin: str):
    """Build authenticated ClobClient for live trading."""
    from py_clob_client.client import ClobClient

    config = get_config(db, user_pin)
    private_key = config.get("private_key_encrypted", "")

    # Decrypt if encrypted (uses same encryption_key as Kite)
    if private_key and settings.encryption_key:
        try:
            from cryptography.fernet import Fernet
            f = Fernet(settings.encryption_key.encode())
            private_key = f.decrypt(private_key.encode()).decode()
        except Exception:
            pass  # Assume it's already plaintext if decryption fails

    if not private_key:
        raise ValueError("No Polymarket private key configured — set it in /polymarket/config")

    return ClobClient(
        host=settings.polymarket_clob_url,
        key=private_key,
        chain_id=settings.polymarket_chain_id,
        signature_type=0,  # EOA (MetaMask)
    )


def place_order(db: Client, user_pin: str, signal_id: str | None = None,
                condition_id: str | None = None, token_id: str | None = None,
                side: str | None = None, price: float | None = None,
                size: float | None = None, order_type: str = "GTC") -> dict:
    """Place an order — from signal or manual params."""
    paper = _is_paper_mode(db, user_pin)

    # If from signal, load signal data
    if signal_id:
        sig = db.table("pm_signals").select("*").eq("id", signal_id).limit(1).execute()
        if not sig.data:
            raise ValueError(f"Signal {signal_id} not found")
        sig = sig.data[0]
        condition_id = condition_id or sig["condition_id"]
        token_id = token_id or sig["token_id"]
        side = side or sig["side"]
        price = price or float(sig["recommended_price"])
        size = size or float(sig["recommended_size"])

    if not all([condition_id, token_id, side, price, size]):
        raise ValueError("Missing required fields: condition_id, token_id, side, price, size")

    # Risk check
    cost_usd = float(price) * float(size)
    allowed, reason = check_limits(db, user_pin, cost_usd, condition_id)
    if not allowed:
        raise ValueError(f"Risk limit exceeded: {reason}")

    # Insert order row
    order_row = {
        "user_pin": user_pin,
        "signal_id": signal_id,
        "condition_id": condition_id,
        "token_id": token_id,
        "side": side,
        "price": float(price),
        "size": float(size),
        "order_type": order_type,
        "paper_mode": paper,
        "status": "pending",
    }
    result = db.table("pm_orders").insert(order_row).execute()
    order = result.data[0] if result.data else order_row
    order_id = order.get("id", "")

    if paper:
        # Paper mode: simulate instant fill
        fill = _simulate_paper_fill(order)
        db.table("pm_orders").update(fill).eq("id", order_id).execute()
        order.update(fill)

        # Update position
        _update_position(db, user_pin, order)
    else:
        # Live mode: submit to Polymarket CLOB
        try:
            clob = _get_clob_client(db, user_pin)
            signed_order = clob.create_order(
                token_id=token_id,
                price=float(price),
                size=float(size),
                side=side.upper(),
                order_type=order_type,
            )
            resp = clob.post_order(signed_order)
            clob_order_id = resp.get("orderID", resp.get("order_id", ""))

            db.table("pm_orders").update({
                "clob_order_id": clob_order_id,
                "status": "live",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", order_id).execute()
            order["clob_order_id"] = clob_order_id
            order["status"] = "live"
        except Exception as e:
            logger.error(f"Live order failed: {e}")
            db.table("pm_orders").update({
                "status": "failed",
                "error_message": str(e)[:500],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", order_id).execute()
            order["status"] = "failed"
            order["error_message"] = str(e)[:500]

    # Update signal status if from signal
    if signal_id:
        db.table("pm_signals").update({"status": "executed"}).eq("id", signal_id).execute()

    log_activity(
        db, event_type="pm_order_placed", entity_type="pm_order",
        entity_id=order_id,
        message=f"{'Paper' if paper else 'Live'} {side} {size} shares @ ${price} on {condition_id[:8]}",
        status="completed",
        metadata_json={"paper": paper, "side": side, "price": float(price), "size": float(size)},
    )

    return order


def _update_position(db: Client, user_pin: str, order: dict):
    """After fill: upsert pm_positions row."""
    token_id = order["token_id"]
    paper = order.get("paper_mode", True)
    fill_price = float(order.get("avg_fill_price", order["price"]))
    fill_size = float(order.get("filled_size", order["size"]))
    side = order.get("side", "BUY").upper()

    # Get market info for question/outcome
    market = db.table("pm_markets").select("question,tokens").eq("condition_id", order["condition_id"]).limit(1).execute()
    question = ""
    outcome = ""
    if market.data:
        question = market.data[0].get("question", "")
        for t in market.data[0].get("tokens", []):
            if t.get("token_id") == token_id:
                outcome = t.get("outcome", "")
                break

    # Check for existing position
    existing = (
        db.table("pm_positions")
        .select("*")
        .eq("user_pin", user_pin)
        .eq("token_id", token_id)
        .eq("paper_mode", paper)
        .eq("status", "open")
        .limit(1)
        .execute()
    )

    now = datetime.now(timezone.utc).isoformat()

    if existing.data and side == "BUY":
        # Accumulate position
        pos = existing.data[0]
        old_size = float(pos["size"])
        old_avg = float(pos["avg_entry_price"])
        new_size = old_size + fill_size
        new_avg = ((old_avg * old_size) + (fill_price * fill_size)) / new_size if new_size > 0 else 0
        cost_basis = new_size * new_avg

        db.table("pm_positions").update({
            "size": new_size,
            "avg_entry_price": round(new_avg, 6),
            "cost_basis": round(cost_basis, 6),
            "market_value": round(new_size * fill_price, 6),
            "unrealized_pnl": round(new_size * fill_price - cost_basis, 6),
            "updated_at": now,
        }).eq("id", pos["id"]).execute()

    elif existing.data and side == "SELL":
        # Reduce position
        pos = existing.data[0]
        old_size = float(pos["size"])
        new_size = max(old_size - fill_size, 0)

        update = {
            "size": new_size,
            "market_value": round(new_size * float(pos["avg_entry_price"]), 6),
            "updated_at": now,
        }
        if new_size == 0:
            update["status"] = "closed"
            update["realized_pnl"] = round(
                fill_size * (fill_price - float(pos["avg_entry_price"])), 6
            )

        db.table("pm_positions").update(update).eq("id", pos["id"]).execute()

    else:
        # New position
        cost_basis = fill_size * fill_price
        db.table("pm_positions").insert({
            "user_pin": user_pin,
            "condition_id": order["condition_id"],
            "token_id": token_id,
            "outcome": outcome,
            "question": question,
            "size": fill_size,
            "avg_entry_price": fill_price,
            "current_price": fill_price,
            "cost_basis": round(cost_basis, 6),
            "market_value": round(cost_basis, 6),
            "unrealized_pnl": 0,
            "unrealized_pnl_pct": 0,
            "strategy": order.get("strategy", "manual"),
            "paper_mode": paper,
            "status": "open",
        }).execute()


def cancel_order(db: Client, user_pin: str, order_id: str) -> dict:
    """Cancel an order."""
    result = db.table("pm_orders").select("*").eq("id", order_id).eq("user_pin", user_pin).limit(1).execute()
    if not result.data:
        raise ValueError("Order not found")

    order = result.data[0]
    if order["status"] not in ("pending", "live"):
        raise ValueError(f"Cannot cancel order with status '{order['status']}'")

    # Cancel on CLOB if live
    if not order["paper_mode"] and order.get("clob_order_id"):
        try:
            clob = _get_clob_client(db, user_pin)
            clob.cancel(order["clob_order_id"])
        except Exception as e:
            logger.error(f"CLOB cancel failed: {e}")

    now = datetime.now(timezone.utc).isoformat()
    db.table("pm_orders").update({
        "status": "cancelled",
        "updated_at": now,
    }).eq("id", order_id).execute()

    order["status"] = "cancelled"
    return order


def get_orders(db: Client, user_pin: str, status: str | None = None,
               limit: int = 50) -> list[dict]:
    """List orders with optional status filter."""
    q = db.table("pm_orders").select("*").eq("user_pin", user_pin).order("created_at", desc=True)
    if status:
        q = q.eq("status", status)
    return q.limit(limit).execute().data
