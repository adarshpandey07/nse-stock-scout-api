"""Market data layer — Gamma API sync + CLOB price fetching."""

import logging
from datetime import datetime, timezone

import httpx
from supabase import Client

from app.config import settings
from app.services.activity import log_activity

logger = logging.getLogger(__name__)

GAMMA_URL = settings.polymarket_gamma_url
CLOB_URL = settings.polymarket_clob_url


async def sync_markets(db: Client, limit: int = 200) -> int:
    """Fetch active markets from Gamma API, upsert into pm_markets."""
    synced = 0
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(
                f"{GAMMA_URL}/events",
                params={"limit": limit, "active": True, "closed": False},
            )
            resp.raise_for_status()
            events = resp.json()
        except Exception as e:
            logger.error(f"Gamma API fetch failed: {e}")
            return 0

    now = datetime.now(timezone.utc).isoformat()

    for event in events:
        for market in event.get("markets", []):
            condition_id = market.get("conditionId") or market.get("condition_id", "")
            if not condition_id:
                continue

            tokens = []
            for token in market.get("tokens", []):
                tokens.append({
                    "token_id": token.get("token_id", ""),
                    "outcome": token.get("outcome", ""),
                    "price": float(token.get("price", 0)),
                })

            yes_price = None
            no_price = None
            for t in tokens:
                if t["outcome"].lower() == "yes":
                    yes_price = t["price"]
                elif t["outcome"].lower() == "no":
                    no_price = t["price"]

            spread = None
            if yes_price is not None and no_price is not None:
                spread = round(yes_price + no_price, 6)

            row = {
                "condition_id": condition_id,
                "question": market.get("question", ""),
                "description": market.get("description", ""),
                "category": event.get("category", ""),
                "end_date": market.get("endDate") or market.get("end_date_iso"),
                "tokens": tokens,
                "volume_24h": float(market.get("volume24hr", 0)),
                "liquidity": float(market.get("liquidity", 0)),
                "yes_price": yes_price,
                "no_price": no_price,
                "spread": spread,
                "active": market.get("active", True),
                "resolution_source": market.get("resolutionSource", ""),
                "tags": event.get("tags", []),
                "last_synced_at": now,
            }

            # Upsert by condition_id
            existing = (
                db.table("pm_markets")
                .select("id")
                .eq("condition_id", condition_id)
                .limit(1)
                .execute()
            )
            if existing.data:
                db.table("pm_markets").update(row).eq("condition_id", condition_id).execute()
            else:
                db.table("pm_markets").insert(row).execute()
            synced += 1

    log_activity(
        db, event_type="pm_market_sync", entity_type="polymarket",
        entity_id="gamma", message=f"Synced {synced} markets from Gamma API",
        status="completed", metadata_json={"count": synced},
    )
    return synced


def get_market(db: Client, condition_id: str) -> dict | None:
    """Get a single market from the cache."""
    result = db.table("pm_markets").select("*").eq("condition_id", condition_id).limit(1).execute()
    return result.data[0] if result.data else None


async def get_orderbook(token_id: str) -> dict:
    """Fetch live orderbook from CLOB API (read-only, no auth)."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{CLOB_URL}/book", params={"token_id": token_id})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Orderbook fetch failed for {token_id}: {e}")
            return {"bids": [], "asks": [], "error": str(e)}


async def get_midpoint(token_id: str) -> float | None:
    """Get current midpoint price from CLOB API."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{CLOB_URL}/midpoint", params={"token_id": token_id})
            resp.raise_for_status()
            data = resp.json()
            return float(data.get("mid", 0))
        except Exception as e:
            logger.error(f"Midpoint fetch failed for {token_id}: {e}")
            return None


async def refresh_prices(db: Client) -> int:
    """Update yes_price, no_price, spread for all active markets."""
    markets = db.table("pm_markets").select("condition_id,tokens").eq("active", True).execute().data
    updated = 0
    now = datetime.now(timezone.utc).isoformat()

    for market in markets:
        tokens = market.get("tokens", [])
        yes_price = None
        no_price = None

        for token in tokens:
            tid = token.get("token_id", "")
            if not tid:
                continue
            mid = await get_midpoint(tid)
            if mid is None:
                continue
            outcome = token.get("outcome", "").lower()
            if outcome == "yes":
                yes_price = mid
            elif outcome == "no":
                no_price = mid

        if yes_price is not None or no_price is not None:
            update = {"last_synced_at": now}
            if yes_price is not None:
                update["yes_price"] = yes_price
            if no_price is not None:
                update["no_price"] = no_price
            if yes_price is not None and no_price is not None:
                update["spread"] = round(yes_price + no_price, 6)

            db.table("pm_markets").update(update).eq("condition_id", market["condition_id"]).execute()
            updated += 1

    return updated


def search_markets(db: Client, query: str = "", category: str = "", active_only: bool = True,
                   limit: int = 50) -> list[dict]:
    """Search cached markets by keyword/category."""
    q = db.table("pm_markets").select("*").order("volume_24h", desc=True)
    if active_only:
        q = q.eq("active", True)
    if category:
        q = q.eq("category", category)
    if query:
        q = q.ilike("question", f"%{query}%")
    return q.limit(limit).execute().data
