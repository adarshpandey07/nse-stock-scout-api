"""News scraping service — uses Firecrawl + BeautifulSoup for article extraction."""
import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from supabase import Client

from app.config import settings
from app.services.activity import log_activity

logger = logging.getLogger(__name__)


async def scrape_moneycontrol(symbol: str) -> list[dict]:
    url = f"https://www.moneycontrol.com/news/tags/{symbol.lower()}.html"
    articles = []
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            if resp.status_code != 200:
                return articles
            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select("li.clearfix")[:10]
            for item in items:
                title_el = item.select_one("h2 a") or item.select_one("a")
                if not title_el:
                    continue
                articles.append({
                    "headline": title_el.get_text(strip=True),
                    "url": title_el.get("href", ""),
                    "summary": (item.select_one("p").get_text(strip=True) if item.select_one("p") else ""),
                    "source_name": "MoneyControl",
                })
        except Exception as e:
            logger.error(f"MoneyControl scrape failed for {symbol}: {e}")
    return articles


async def scrape_with_firecrawl(url: str, source_name: str) -> list[dict]:
    if not settings.firecrawl_api_key:
        return []
    articles = []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.firecrawl.dev/v0/scrape",
                json={"url": url, "pageOptions": {"onlyMainContent": True}},
                headers={"Authorization": f"Bearer {settings.firecrawl_api_key}"},
            )
            if resp.status_code != 200:
                return articles
            content = resp.json().get("data", {}).get("markdown", "")
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("##") or (line.startswith("[") and "](" in line):
                    headline = line.lstrip("#").strip()
                    if len(headline) > 20:
                        articles.append({
                            "headline": headline[:500],
                            "url": url,
                            "summary": "",
                            "source_name": source_name,
                        })
    except Exception as e:
        logger.error(f"Firecrawl scrape failed for {url}: {e}")
    return articles


async def scrape_all_sources(db: Client, symbol: str | None = None) -> int:
    sources = db.table("news_sources").select("*").eq("enabled", True).execute().data
    total = 0

    for source in sources:
        if source["name"] == "MoneyControl" and symbol:
            articles = await scrape_moneycontrol(symbol)
        else:
            articles = await scrape_with_firecrawl(source["url"], source["name"])

        for article in articles:
            exists = db.table("stock_news").select("id").eq("headline", article["headline"]).limit(1).execute()
            if exists.data:
                continue
            db.table("stock_news").insert({
                "symbol": symbol,
                "headline": article["headline"],
                "summary": article.get("summary", ""),
                "source_id": source["id"],
                "source_name": source["name"],
                "url": article.get("url", ""),
                "news_type": "direct" if symbol else "market",
            }).execute()
            total += 1

        db.table("news_sources").update({
            "last_scraped_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", source["id"]).execute()

    log_activity(db, event_type="news_scraped", entity_type="news",
                 entity_id=symbol or "all",
                 message=f"Scraped {total} articles from {len(sources)} sources",
                 status="completed", metadata_json={"count": total})
    return total
