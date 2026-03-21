"""Position tracking, P&L calculation, snapshots, resolution detection."""

import logging
from datetime import date, datetime, timezone

import httpx
from supabase import Client

from app.config import settings
from app.services.activity import log_activity

logger = logging.getLogger(__name__)


def get_positions(db: Client, user_pin: str, status: str = "open",
                  limit: int = 100) -> list[dict]:
    """List positions with optional status filter."""
    q = (
        db.table("pm_positions")
        .select("*")
        .eq("user_pin", user_pin)
        .order("created_at", desc=True)
    )
    if status:
        q = q.eq("status", status)
    return q.limit(limit).execute().data


def refresh_position_prices(db: Client, user_pin: str) -> int:
    """Update current_price, market_value, unrealized_pnl for all open positions."""
    positions = get_positions(db, user_pin, status="open")
    updated = 0
    now = datetime.now(timezone.utc).isoformat()

    for pos in positions:
        # Look up current price from pm_markets cache
        market = (
            db.table("pm_markets")
            .select("tokens")
            .eq("condition_id", pos["condition_id"])
            .limit(1)
            .execute()
        )
        if not market.data:
            continue

        current_price = None
        for token in market.data[0].get("tokens", []):
            if token.get("token_id") == pos["token_id"]:
                current_price = float(token.get("price", 0))
                break

        if current_price is None:
            continue

        size = float(pos["size"])
        cost_basis = float(pos["cost_basis"])
        market_value = round(size * current_price, 6)
        unrealized_pnl = round(market_value - cost_basis, 6)
        unrealized_pnl_pct = round((unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0, 2)

        db.table("pm_positions").update({
            "current_price": current_price,
            "market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "updated_at": now,
        }).eq("id", pos["id"]).execute()
        updated += 1

    return updated


def get_pnl_summary(db: Client, user_pin: str) -> dict:
    """Aggregate P&L across all positions."""
    open_pos = get_positions(db, user_pin, status="open")
    closed_pos = get_positions(db, user_pin, status="closed")
    resolved_pos = get_positions(db, user_pin, status="resolved")

    total_invested = sum(float(p.get("cost_basis", 0)) for p in open_pos)
    total_market_value = sum(float(p.get("market_value", 0)) for p in open_pos)
    total_unrealized = sum(float(p.get("unrealized_pnl", 0)) for p in open_pos)
    total_realized = (
        sum(float(p.get("realized_pnl", 0)) for p in closed_pos) +
        sum(float(p.get("realized_pnl", 0)) for p in resolved_pos)
    )

    return {
        "total_invested": round(total_invested, 2),
        "total_market_value": round(total_market_value, 2),
        "total_unrealized_pnl": round(total_unrealized, 2),
        "total_realized_pnl": round(total_realized, 2),
        "open_positions": len(open_pos),
        "closed_positions": len(closed_pos),
        "resolved_positions": len(resolved_pos),
    }


def take_snapshot(db: Client, user_pin: str) -> dict:
    """Insert pm_pnl_snapshots row for today."""
    summary = get_pnl_summary(db, user_pin)
    today = date.today().isoformat()

    # Check if already snapped today
    existing = (
        db.table("pm_pnl_snapshots")
        .select("id")
        .eq("user_pin", user_pin)
        .eq("snapshot_date", today)
        .limit(1)
        .execute()
    )

    # Build strategy breakdown
    open_pos = get_positions(db, user_pin, status="open")
    by_strategy = {}
    for pos in open_pos:
        strat = pos.get("strategy", "unknown")
        if strat not in by_strategy:
            by_strategy[strat] = {"invested": 0, "pnl": 0}
        by_strategy[strat]["invested"] += float(pos.get("cost_basis", 0))
        by_strategy[strat]["pnl"] += float(pos.get("unrealized_pnl", 0))

    config = db.table("pm_config").select("paper_mode").eq("user_pin", user_pin).limit(1).execute()
    paper = config.data[0].get("paper_mode", True) if config.data else True

    row = {
        "user_pin": user_pin,
        "snapshot_date": today,
        "total_invested": summary["total_invested"],
        "total_market_value": summary["total_market_value"],
        "total_unrealized_pnl": summary["total_unrealized_pnl"],
        "total_realized_pnl": summary["total_realized_pnl"],
        "open_positions": summary["open_positions"],
        "strategy_breakdown": by_strategy,
        "paper_mode": paper,
    }

    if existing.data:
        db.table("pm_pnl_snapshots").update(row).eq("id", existing.data[0]["id"]).execute()
    else:
        db.table("pm_pnl_snapshots").insert(row).execute()

    return row


async def check_resolutions(db: Client) -> int:
    """Check if any markets have resolved. Settle positions accordingly."""
    # Fetch markets that have open positions
    open_positions = (
        db.table("pm_positions")
        .select("condition_id")
        .eq("status", "open")
        .execute()
        .data
    )
    if not open_positions:
        return 0

    condition_ids = list(set(p["condition_id"] for p in open_positions))
    settled = 0

    for condition_id in condition_ids:
        # Check Gamma API for resolution
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{settings.polymarket_gamma_url}/markets/{condition_id}",
                )
                if resp.status_code != 200:
                    continue
                market_data = resp.json()
        except Exception as e:
            logger.error(f"Resolution check failed for {condition_id}: {e}")
            continue

        # Check if resolved
        resolved = market_data.get("resolved", False)
        if not resolved:
            continue

        winning_outcome = market_data.get("outcome", "").lower()
        if not winning_outcome:
            continue

        # Settle all open positions for this market
        positions = (
            db.table("pm_positions")
            .select("*")
            .eq("condition_id", condition_id)
            .eq("status", "open")
            .execute()
            .data
        )

        now = datetime.now(timezone.utc).isoformat()
        for pos in positions:
            outcome = pos.get("outcome", "").lower()
            size = float(pos["size"])
            cost_basis = float(pos["cost_basis"])

            if outcome == winning_outcome:
                # Winner: each share pays $1.00
                payout = size * 1.0
                realized_pnl = round(payout - cost_basis, 6)
            else:
                # Loser: shares worth $0
                realized_pnl = round(-cost_basis, 6)

            db.table("pm_positions").update({
                "status": "resolved",
                "resolved_outcome": winning_outcome,
                "realized_pnl": realized_pnl,
                "current_price": 1.0 if outcome == winning_outcome else 0.0,
                "market_value": size if outcome == winning_outcome else 0,
                "unrealized_pnl": 0,
                "updated_at": now,
            }).eq("id", pos["id"]).execute()

            # Update strategy stats
            _update_strategy_stats(db, pos["user_pin"], pos.get("strategy", "unknown"),
                                   won=(outcome == winning_outcome),
                                   invested=cost_basis, returned=payout if outcome == winning_outcome else 0,
                                   paper=pos.get("paper_mode", True))

            settled += 1

        # Mark market as inactive
        db.table("pm_markets").update({"active": False}).eq("condition_id", condition_id).execute()

    if settled > 0:
        log_activity(
            db, event_type="pm_settled", entity_type="polymarket",
            entity_id="batch",
            message=f"Settled {settled} positions across {len(condition_ids)} markets",
            status="completed", metadata_json={"settled": settled},
        )

    return settled


def _update_strategy_stats(db: Client, user_pin: str, strategy: str,
                           won: bool, invested: float, returned: float,
                           paper: bool = True):
    """Update pm_strategy_stats after a position resolves."""
    existing = (
        db.table("pm_strategy_stats")
        .select("*")
        .eq("user_pin", user_pin)
        .eq("strategy", strategy)
        .eq("paper_mode", paper)
        .limit(1)
        .execute()
    )

    now = datetime.now(timezone.utc).isoformat()

    if existing.data:
        stats = existing.data[0]
        signals_exec = int(stats.get("signals_executed", 0)) + 1
        wins = int(stats.get("winning_trades", 0)) + (1 if won else 0)
        losses = int(stats.get("losing_trades", 0)) + (0 if won else 1)
        total_inv = float(stats.get("total_invested", 0)) + invested
        total_ret = float(stats.get("total_returned", 0)) + returned
        net_pnl = round(total_ret - total_inv, 2)
        win_rate = round(wins / signals_exec * 100, 1) if signals_exec > 0 else 0

        db.table("pm_strategy_stats").update({
            "signals_executed": signals_exec,
            "winning_trades": wins,
            "losing_trades": losses,
            "total_invested": total_inv,
            "total_returned": total_ret,
            "net_pnl": net_pnl,
            "win_rate": win_rate,
            "updated_at": now,
        }).eq("id", stats["id"]).execute()
    else:
        db.table("pm_strategy_stats").insert({
            "user_pin": user_pin,
            "strategy": strategy,
            "total_signals": 1,
            "signals_executed": 1,
            "winning_trades": 1 if won else 0,
            "losing_trades": 0 if won else 1,
            "total_invested": invested,
            "total_returned": returned,
            "net_pnl": round(returned - invested, 2),
            "win_rate": 100 if won else 0,
            "paper_mode": paper,
        }).execute()
