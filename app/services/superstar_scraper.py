"""Superstar portfolio scraper — scrapes Trendlyne for investor holdings."""
import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from supabase import Client

from app.services.activity import log_activity

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


async def scrape_investor_holdings(db: Client, investor_id: str) -> int:
    result = db.table("superstar_investors").select("*").eq("id", investor_id).limit(1).execute()
    if not result.data:
        raise ValueError(f"Investor {investor_id} not found")
    investor = result.data[0]

    name_slug = investor["name"].lower().replace(" ", "-").replace("'", "")
    url = f"https://trendlyne.com/superstar/{name_slug}/"

    count = 0
    async with httpx.AsyncClient(timeout=20) as cli:
        try:
            resp = await cli.get(url, headers=HEADERS)
            if resp.status_code != 200:
                return 0
            soup = BeautifulSoup(resp.text, "html.parser")
            table = soup.select_one("table.superstar-table") or soup.select_one("table")
            if not table:
                return 0

            rows = table.select("tbody tr")
            current_quarter = f"Q{(datetime.now().month - 1) // 3 + 1} {datetime.now().year}"

            for row in rows:
                cells = row.select("td")
                if len(cells) < 4:
                    continue
                symbol_el = cells[0].select_one("a")
                symbol = symbol_el.get_text(strip=True).upper() if symbol_el else cells[0].get_text(strip=True).upper()
                try:
                    qty = int(cells[1].get_text(strip=True).replace(",", ""))
                except (ValueError, IndexError):
                    qty = 0
                try:
                    value = float(cells[2].get_text(strip=True).replace(",", ""))
                except (ValueError, IndexError):
                    value = 0

                change_text = cells[3].get_text(strip=True).lower() if len(cells) > 3 else "hold"
                if "new" in change_text:
                    change_type = "new"
                elif "increase" in change_text or "+" in change_text:
                    change_type = "increased"
                elif "decrease" in change_text or "-" in change_text:
                    change_type = "decreased"
                elif "sold" in change_text or "exit" in change_text:
                    change_type = "sold"
                else:
                    change_type = "hold"

                db.table("superstar_holdings").insert({
                    "investor_id": investor["id"],
                    "symbol": symbol,
                    "qty": qty,
                    "value": value,
                    "change_type": change_type,
                    "quarter": current_quarter,
                    "reported_date": datetime.now(timezone.utc).date().isoformat(),
                }).execute()
                count += 1
        except Exception as e:
            logger.error(f"Trendlyne scrape failed for {investor['name']}: {e}")

    log_activity(db, event_type="superstar_scraped", entity_type="superstar",
                 entity_id=str(investor["id"]),
                 message=f"Scraped {count} holdings for {investor['name']}",
                 status="completed", metadata_json={"count": count})
    return count


async def scrape_all_investors(db: Client) -> int:
    investors = db.table("superstar_investors").select("*").eq("is_active", True).execute().data
    total = 0
    for inv in investors:
        count = await scrape_investor_holdings(db, str(inv["id"]))
        total += count
    return total


def get_recent_changes(db: Client, limit: int = 50) -> list[dict]:
    holdings = (
        db.table("superstar_holdings")
        .select("*")
        .neq("change_type", "hold")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )
    result = []
    for h in holdings:
        inv = db.table("superstar_investors").select("name").eq("id", h["investor_id"]).limit(1).execute()
        result.append({
            "investor_name": inv.data[0]["name"] if inv.data else "Unknown",
            "symbol": h["symbol"],
            "change_type": h["change_type"],
            "qty": h["qty"],
            "value": float(h.get("value", 0)),
            "quarter": h["quarter"],
            "reported_date": h.get("reported_date"),
        })
    return result
