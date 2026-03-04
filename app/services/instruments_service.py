"""NSE instrument list management — refresh from NSE public data or Kite."""
import csv
import io
import logging

import httpx
from supabase import Client

from app.services.activity import log_activity

logger = logging.getLogger(__name__)

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.nseindia.com/",
}


async def refresh_instruments_from_nse(db: Client) -> int:
    """Fetch equity list from NSE public CSV and upsert into nse_stocks.

    Uses NSE's public equity stock listing CSV — no API key needed.
    """
    url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"

    async with httpx.AsyncClient(headers=NSE_HEADERS, follow_redirects=True, timeout=30) as client:
        # Hit NSE homepage first to get cookies
        await client.get("https://www.nseindia.com/")
        resp = await client.get(url)
        resp.raise_for_status()

    csv_content = resp.text
    reader = csv.DictReader(io.StringIO(csv_content))
    count = 0

    for row in reader:
        row = {k.strip(): v.strip() if v else v for k, v in row.items()}
        symbol = row.get("SYMBOL", "")
        name = row.get("NAME OF COMPANY", "")
        series = row.get(" SERIES", row.get("SERIES", ""))
        isin = row.get(" ISIN NUMBER", row.get("ISIN NUMBER", ""))

        if not symbol or series != "EQ":
            continue

        existing = db.table("nse_stocks").select("symbol").eq("symbol", symbol).limit(1).execute()
        if existing.data:
            db.table("nse_stocks").update({
                "name": name,
                "isin": isin or "",
                "is_active": True,
            }).eq("symbol", symbol).execute()
        else:
            db.table("nse_stocks").insert({
                "symbol": symbol,
                "name": name,
                "isin": isin or "",
                "series": "EQ",
                "is_active": True,
            }).execute()
            count += 1

    log_activity(db, event_type="instruments_refreshed", entity_type="nse_stocks",
                 entity_id="all", message=f"Refreshed instruments from NSE: {count} new",
                 status="completed", metadata_json={"new_count": count, "source": "nse_equity_csv"})
    return count


def refresh_instruments_from_kite(db: Client, api_key: str, access_token: str) -> int:
    """Fetch full instrument list from Kite and upsert into nse_stocks (requires Kite credentials)."""
    try:
        from kiteconnect import KiteConnect
    except ImportError:
        logger.warning("kiteconnect not installed — use refresh_instruments_from_nse instead")
        return 0

    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)

    instruments = kite.instruments("NSE")
    count = 0

    for inst in instruments:
        if inst.get("segment") != "NSE" or inst.get("instrument_type") != "EQ":
            continue

        symbol = inst["tradingsymbol"]
        existing = db.table("nse_stocks").select("symbol").eq("symbol", symbol).limit(1).execute()

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
