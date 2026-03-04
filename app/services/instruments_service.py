"""NSE instrument list management — refresh from Kite or manual sources."""
import logging

from kiteconnect import KiteConnect
from supabase import Client

from app.services.activity import log_activity

logger = logging.getLogger(__name__)


def refresh_instruments_from_kite(db: Client, api_key: str, access_token: str) -> int:
    """Fetch full instrument list from Kite and upsert into nse_stocks."""
    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)

    instruments = kite.instruments("NSE")
    count = 0

    for inst in instruments:
        if inst.get("segment") != "NSE" or inst.get("instrument_type") != "EQ":
            continue

        symbol = inst["tradingsymbol"]
        existing = db.table("nse_stocks").select("id").eq("symbol", symbol).limit(1).execute()

        if existing.data:
            db.table("nse_stocks").update({
                "name": inst.get("name", ""),
                "isin": inst.get("isin", "") or "",
            }).eq("symbol", symbol).execute()
        else:
            db.table("nse_stocks").insert({
                "symbol": symbol,
                "name": inst.get("name", ""),
                "isin": inst.get("isin", "") or "",
                "series": "EQ",
                "is_active": True,
            }).execute()
            count += 1

    log_activity(db, event_type="instruments_refreshed", entity_type="nse_stocks",
                 entity_id="all", message=f"Refreshed instruments: {count} new",
                 status="completed", metadata_json={"new_count": count, "total_fetched": len(instruments)})
    return count


def get_all_stocks(db: Client, search: str = "", sector: str = "",
                   limit: int = 100, offset: int = 0) -> list[dict]:
    q = db.table("nse_stocks").select("*").eq("is_active", True)
    if search:
        q = q.or_(f"symbol.ilike.%{search}%,name.ilike.%{search}%")
    if sector:
        q = q.ilike("sector", f"%{sector}%")
    result = q.order("symbol").range(offset, offset + limit - 1).execute()
    return result.data


def get_stock_by_symbol(db: Client, symbol: str) -> dict | None:
    result = db.table("nse_stocks").select("*").eq("symbol", symbol.upper()).limit(1).execute()
    return result.data[0] if result.data else None
