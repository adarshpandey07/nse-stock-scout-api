"""Fundamentals data management — scrape from public sources via httpx."""
import logging

import httpx
from supabase import Client

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


async def fetch_fundamentals_screener(db: Client, symbol: str) -> dict | None:
    """Fetch fundamentals from Screener.in API (public data)."""
    url = f"https://www.screener.in/api/company/{symbol}/consolidated/"

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(url, headers=HEADERS)
            if resp.status_code != 200:
                url2 = f"https://www.screener.in/api/company/{symbol}/"
                resp = await client.get(url2, headers=HEADERS)
                if resp.status_code != 200:
                    logger.warning(f"Screener returned {resp.status_code} for {symbol}")
                    return None
            data = resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch fundamentals for {symbol}: {e}")
            return None

    wh = data.get("warehouse_set", {})
    if not wh:
        return None

    updates = {
        "pe": wh.get("pe"),
        "pb": wh.get("price_to_book_value"),
        "roe": wh.get("return_on_equity"),
        "roce": wh.get("roce"),
        "debt_equity": wh.get("debt_to_equity"),
        "market_cap": wh.get("market_cap"),
        "dividend_yield": wh.get("dividend_yield"),
        "eps": wh.get("eps"),
        "book_value": wh.get("book_value"),
        "face_value": wh.get("face_value"),
        "promoter_holding": wh.get("promoter_holding"),
        "current_price": wh.get("current_price", 0),
        "sales_growth_5y": wh.get("revenue_growth_5years", 0) or 0,
        "profit_growth_5y": wh.get("profit_growth_5years", 0) or 0,
        "eps_growth_yoy": wh.get("eps_growth_yoy", 0) or 0,
    }

    existing = db.table("stock_fundamentals").select("id").eq("symbol", symbol).limit(1).execute()
    if existing.data:
        result = db.table("stock_fundamentals").update(updates).eq("symbol", symbol).execute()
    else:
        updates["symbol"] = symbol
        result = db.table("stock_fundamentals").insert(updates).execute()

    return result.data[0] if result.data else updates


def get_fundamentals(db: Client, symbol: str) -> dict | None:
    result = db.table("stock_fundamentals").select("*").eq("symbol", symbol.upper()).limit(1).execute()
    return result.data[0] if result.data else None


async def refresh_all_fundamentals(db: Client, symbols: list[str] | None = None) -> int:
    if not symbols:
        stocks = db.table("nse_stocks").select("symbol").eq("is_active", True).execute()
        symbols = [s["symbol"] for s in stocks.data]

    count = 0
    for symbol in symbols:
        result = await fetch_fundamentals_screener(db, symbol)
        if result:
            count += 1
    return count
