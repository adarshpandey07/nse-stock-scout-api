"""Risk management — Kelly criterion sizing, exposure limits, kill switch."""

import logging
from datetime import datetime, timezone

from supabase import Client

from app.config import settings
from app.services.activity import log_activity

logger = logging.getLogger(__name__)

TAKER_FEE = 0.003  # 0.30%


def kelly_size(
    estimated_prob: float,
    market_price: float,
    bankroll: float,
    fraction: float = 0.25,
) -> float:
    """Calculate Kelly criterion position size in USD.

    f* = (bp - q) / b  then multiply by fraction (default 1/4 Kelly).
    - estimated_prob = Claude's probability estimate (0-1)
    - market_price = current market price to buy at (0-1)
    - bankroll = total capital available
    - fraction = Kelly fraction (0.25 = quarter Kelly, safest)
    """
    if market_price <= 0 or market_price >= 1 or estimated_prob <= 0 or estimated_prob >= 1:
        return 0.0

    # Decimal odds: what you win per $1 wagered
    b = (1.0 / market_price) - 1.0
    p = estimated_prob
    q = 1.0 - p

    if b <= 0:
        return 0.0

    f_star = (b * p - q) / b
    if f_star <= 0:
        return 0.0  # No edge — don't bet

    # Apply fraction and bankroll
    size_usd = f_star * fraction * bankroll

    # Account for taker fee
    size_usd = size_usd * (1 - TAKER_FEE)

    return round(max(size_usd, 0), 2)


def get_config(db: Client, user_pin: str) -> dict:
    """Get user's pm_config, or create default if none exists."""
    result = db.table("pm_config").select("*").eq("user_pin", user_pin).limit(1).execute()
    if result.data:
        return result.data[0]

    # Create default config
    row = {
        "user_pin": user_pin,
        "paper_mode": True,
        "max_position_usd": 50,
        "max_total_exposure_usd": 500,
        "kelly_fraction": 0.25,
        "auto_trade": False,
        "strategies_enabled": ["arb"],
    }
    result = db.table("pm_config").insert(row).execute()
    return result.data[0] if result.data else row


def get_exposure(db: Client, user_pin: str) -> dict:
    """Calculate total exposure across all open positions."""
    positions = (
        db.table("pm_positions")
        .select("cost_basis,strategy,condition_id")
        .eq("user_pin", user_pin)
        .eq("status", "open")
        .execute()
        .data
    )

    total = 0.0
    by_strategy = {}
    by_market = {}

    for pos in positions:
        cost = float(pos.get("cost_basis", 0))
        total += cost
        strat = pos.get("strategy", "unknown")
        by_strategy[strat] = by_strategy.get(strat, 0) + cost
        cid = pos.get("condition_id", "")
        by_market[cid] = by_market.get(cid, 0) + cost

    config = get_config(db, user_pin)
    max_exposure = float(config.get("max_total_exposure_usd", 500))

    return {
        "total_exposure": round(total, 2),
        "by_strategy": by_strategy,
        "by_market": by_market,
        "remaining_capacity": round(max(max_exposure - total, 0), 2),
        "max_total_exposure_usd": max_exposure,
    }


def check_limits(db: Client, user_pin: str, proposed_size_usd: float,
                 condition_id: str = "") -> tuple[bool, str]:
    """Pre-trade risk check. Returns (allowed, reason)."""
    # Global paper mode override
    if settings.polymarket_paper_mode:
        pass  # Paper mode always allowed, but we still check sizing

    config = get_config(db, user_pin)
    max_position = float(config.get("max_position_usd", 50))
    max_total = float(config.get("max_total_exposure_usd", 500))

    # Check per-position limit
    if proposed_size_usd > max_position:
        return False, f"Size ${proposed_size_usd} exceeds per-position limit ${max_position}"

    # Check total exposure
    exposure = get_exposure(db, user_pin)
    if exposure["total_exposure"] + proposed_size_usd > max_total:
        return False, (
            f"Total exposure would be ${exposure['total_exposure'] + proposed_size_usd:.2f}, "
            f"exceeds max ${max_total}"
        )

    # Check single-market concentration (max 20% of total capacity)
    if condition_id:
        market_exposure = exposure["by_market"].get(condition_id, 0)
        max_per_market = max_total * 0.20
        if market_exposure + proposed_size_usd > max_per_market:
            return False, (
                f"Market concentration would be ${market_exposure + proposed_size_usd:.2f}, "
                f"exceeds 20% limit ${max_per_market:.2f}"
            )

    return True, "OK"


def kill_switch(db: Client, user_pin: str) -> int:
    """Emergency: cancel all live orders, disable auto-trade."""
    # Cancel all pending/live orders
    orders = (
        db.table("pm_orders")
        .select("id,clob_order_id,paper_mode")
        .eq("user_pin", user_pin)
        .in_("status", ["pending", "live"])
        .execute()
        .data
    )

    cancelled = 0
    now = datetime.now(timezone.utc).isoformat()
    for order in orders:
        db.table("pm_orders").update({
            "status": "cancelled",
            "error_message": "Kill switch activated",
            "updated_at": now,
        }).eq("id", order["id"]).execute()
        cancelled += 1

    # Disable auto-trade
    db.table("pm_config").update({
        "auto_trade": False,
        "updated_at": now,
    }).eq("user_pin", user_pin).execute()

    log_activity(
        db, event_type="pm_kill_switch", entity_type="polymarket",
        entity_id=user_pin,
        message=f"Kill switch: cancelled {cancelled} orders, disabled auto-trade",
        status="completed", metadata_json={"cancelled": cancelled},
    )
    return cancelled
