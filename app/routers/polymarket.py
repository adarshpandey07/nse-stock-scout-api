"""Polymarket Trading Module — FastAPI Router."""

from fastapi import APIRouter, HTTPException, Query

from app.dependencies import AdminUser, CurrentUser, DB
from app.schemas.polymarket import (
    PmConfigOut, PmConfigUpdate, PmDashboardOut, PmMarketOut,
    PmOrderOut, PmOrderRequest, PmPnlSnapshotOut, PmPositionOut,
    PmSignalDecision, PmSignalOut, PmStrategyStatsOut,
)
from app.services.polymarket import market_service, order_service, position_service, risk_manager
from app.services.polymarket.scanners import (
    run_arb_scanner, run_cross_arb_scanner, run_mispricing_scanner, run_news_reaction_scanner,
)
from app.services.polymarket.settlement_service import run_settlement

router = APIRouter(prefix="/polymarket", tags=["polymarket"])


# ── Config ──


@router.get("/config", response_model=PmConfigOut)
def get_config(db: DB, user: CurrentUser, user_pin: str = Query(...)):
    return risk_manager.get_config(db, user_pin)


@router.put("/config", response_model=PmConfigOut)
def update_config(req: PmConfigUpdate, db: DB, user: CurrentUser,
                  user_pin: str = Query(...)):
    from datetime import datetime, timezone
    config = risk_manager.get_config(db, user_pin)
    updates = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return config
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    db.table("pm_config").update(updates).eq("user_pin", user_pin).execute()
    return risk_manager.get_config(db, user_pin)


# ── Markets ──


@router.get("/markets", response_model=list[PmMarketOut])
def list_markets(
    db: DB, _user: CurrentUser,
    query: str = Query(""),
    category: str = Query(""),
    active: bool = Query(True),
    limit: int = Query(50, le=200),
):
    return market_service.search_markets(db, query=query, category=category,
                                         active_only=active, limit=limit)


@router.get("/markets/{condition_id}", response_model=PmMarketOut)
def get_market(condition_id: str, db: DB, _user: CurrentUser):
    m = market_service.get_market(db, condition_id)
    if not m:
        raise HTTPException(status_code=404, detail="Market not found")
    return m


@router.get("/markets/{condition_id}/orderbook")
async def get_orderbook(condition_id: str, _user: CurrentUser):
    # Get token_id from condition_id — need to look it up
    # For now, pass condition_id as token_id (caller can override via query param)
    return await market_service.get_orderbook(condition_id, condition_id)


@router.post("/markets/sync")
async def sync_markets(db: DB, _user: AdminUser, limit: int = Query(200, le=500)):
    count = await market_service.sync_markets(db, limit=limit)
    return {"synced": count}


# ── Signals ──


@router.get("/signals", response_model=list[PmSignalOut])
def list_signals(
    db: DB, _user: CurrentUser,
    status: str = Query(None),
    strategy: str = Query(None),
    limit: int = Query(50, le=200),
):
    q = db.table("pm_signals").select("*").order("created_at", desc=True)
    if status:
        q = q.eq("status", status)
    if strategy:
        q = q.eq("strategy", strategy)
    return q.limit(limit).execute().data


@router.post("/signals/{signal_id}/approve", response_model=PmSignalOut)
def approve_signal(signal_id: str, req: PmSignalDecision, db: DB, user: CurrentUser):
    result = db.table("pm_signals").select("*").eq("id", signal_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Signal not found")

    signal = result.data[0]
    if signal["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Signal already {signal['status']}")

    from datetime import datetime, timezone
    db.table("pm_signals").update({
        "status": "approved",
    }).eq("id", signal_id).execute()

    # Auto-execute if approved
    try:
        order_service.place_order(
            db, user_pin=req.decided_by,
            signal_id=signal_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return db.table("pm_signals").select("*").eq("id", signal_id).limit(1).execute().data[0]


@router.post("/signals/{signal_id}/reject", response_model=PmSignalOut)
def reject_signal(signal_id: str, db: DB, _user: CurrentUser):
    result = db.table("pm_signals").select("*").eq("id", signal_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Signal not found")

    db.table("pm_signals").update({"status": "rejected"}).eq("id", signal_id).execute()
    return db.table("pm_signals").select("*").eq("id", signal_id).limit(1).execute().data[0]


# ── Orders ──


@router.get("/orders", response_model=list[PmOrderOut])
def list_orders(
    db: DB, _user: CurrentUser,
    user_pin: str = Query(...),
    status: str = Query(None),
    limit: int = Query(50, le=200),
):
    return order_service.get_orders(db, user_pin, status=status, limit=limit)


@router.post("/orders", response_model=PmOrderOut)
def create_order(req: PmOrderRequest, db: DB, user: CurrentUser,
                 user_pin: str = Query(...)):
    try:
        return order_service.place_order(
            db, user_pin=user_pin,
            signal_id=req.signal_id,
            condition_id=req.condition_id,
            token_id=req.token_id,
            side=req.side,
            price=float(req.price) if req.price else None,
            size=float(req.size) if req.size else None,
            order_type=req.order_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/orders/{order_id}", response_model=PmOrderOut)
def cancel_order(order_id: str, db: DB, user: CurrentUser,
                 user_pin: str = Query(...)):
    try:
        return order_service.cancel_order(db, user_pin, order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Positions ──


@router.get("/positions", response_model=list[PmPositionOut])
def list_positions(
    db: DB, _user: CurrentUser,
    user_pin: str = Query(...),
    status: str = Query("open"),
    limit: int = Query(100, le=500),
):
    return position_service.get_positions(db, user_pin, status=status, limit=limit)


@router.post("/positions/refresh")
def refresh_positions(db: DB, _user: CurrentUser, user_pin: str = Query(...)):
    updated = position_service.refresh_position_prices(db, user_pin)
    return {"updated": updated}


# ── Dashboard ──


@router.get("/dashboard", response_model=PmDashboardOut)
def get_dashboard(db: DB, _user: CurrentUser, user_pin: str = Query(...)):
    summary = position_service.get_pnl_summary(db, user_pin)
    config = risk_manager.get_config(db, user_pin)

    # Recent signals
    signals = (
        db.table("pm_signals")
        .select("*")
        .order("created_at", desc=True)
        .limit(10)
        .execute()
        .data
    )

    # Recent orders
    orders = order_service.get_orders(db, user_pin, limit=10)

    # Strategy stats
    stats = (
        db.table("pm_strategy_stats")
        .select("*")
        .eq("user_pin", user_pin)
        .execute()
        .data
    )

    # Pending signals count
    pending = (
        db.table("pm_signals")
        .select("id", count="exact")
        .eq("status", "pending")
        .execute()
    )

    return {
        "total_invested": summary["total_invested"],
        "total_market_value": summary["total_market_value"],
        "total_unrealized_pnl": summary["total_unrealized_pnl"],
        "total_realized_pnl": summary["total_realized_pnl"],
        "open_positions": summary["open_positions"],
        "pending_signals": pending.count if pending.count else 0,
        "recent_signals": signals,
        "recent_orders": orders,
        "strategy_stats": stats,
        "paper_mode": config.get("paper_mode", True),
    }


# ── Stats & History ──


@router.get("/stats", response_model=list[PmStrategyStatsOut])
def get_stats(db: DB, _user: CurrentUser, user_pin: str = Query(...)):
    return (
        db.table("pm_strategy_stats")
        .select("*")
        .eq("user_pin", user_pin)
        .execute()
        .data
    )


@router.get("/pnl-history", response_model=list[PmPnlSnapshotOut])
def get_pnl_history(
    db: DB, _user: CurrentUser,
    user_pin: str = Query(...),
    limit: int = Query(30, le=365),
):
    return (
        db.table("pm_pnl_snapshots")
        .select("*")
        .eq("user_pin", user_pin)
        .order("snapshot_date", desc=True)
        .limit(limit)
        .execute()
        .data
    )


# ── Scanner Controls (Admin) ──


@router.post("/scan/arb")
def trigger_arb_scan(db: DB, _user: AdminUser):
    count = run_arb_scanner(db)
    return {"signals": count}


@router.post("/scan/mispricing")
async def trigger_mispricing_scan(db: DB, _user: AdminUser,
                                   bankroll: float = Query(500)):
    count = await run_mispricing_scanner(db, bankroll=bankroll)
    return {"signals": count}


@router.post("/scan/news")
async def trigger_news_scan(db: DB, _user: AdminUser,
                             bankroll: float = Query(500)):
    count = await run_news_reaction_scanner(db, bankroll=bankroll)
    return {"signals": count}


@router.post("/scan/settle")
async def trigger_settlement(db: DB, _user: AdminUser):
    count = await run_settlement(db)
    return {"settled": count}


@router.post("/kill-switch")
def trigger_kill_switch(db: DB, _user: AdminUser, user_pin: str = Query(...)):
    cancelled = risk_manager.kill_switch(db, user_pin)
    return {"cancelled": cancelled, "auto_trade": False}
