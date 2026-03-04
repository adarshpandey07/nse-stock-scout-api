"""
NSE Stock Scout — Cron Job Runner

Schedule:
  4:00 PM IST: Bhavcopy + VCP + Tight scanners
  4:05 PM: Portfolio snapshots (all 3 users)
  4:10 PM: F1/F2/F3 scan (if fundamentals fresh)
  4:15 PM: Generate action items
  4:30 PM: Telegram daily summary
  3x daily (8:30 AM, 1:30 PM, 5:30 PM IST): News scraping
  Weekly Sunday 7:30 PM: Refresh instruments + fundamentals
"""
import asyncio
import logging
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db
from app.services.bhavcopy import fetch_bhavcopy
from app.services.scanners import run_tight_scanner, run_vcp_scanner
from app.utils import last_trading_day

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_PINS = ["aadarsh", "parth", "vardhaman"]


async def job_daily_scan():
    """4:00 PM — Bhavcopy fetch + both scanners."""
    today = last_trading_day()
    db = get_db()
    try:
        logger.info(f"[4:00 PM] Starting daily scan for {today}")
        run = await fetch_bhavcopy(db, today)
        logger.info(f"Fetch completed: {run}")

        vcp_count = run_vcp_scanner(db, today)
        logger.info(f"VCP scanner: {vcp_count} results")

        tight_count = run_tight_scanner(db, today)
        logger.info(f"Tight scanner: {tight_count} results")
    except Exception as e:
        logger.error(f"Daily scan failed: {e}")


async def job_portfolio_snapshots():
    """4:05 PM — Snapshot portfolio for all 3 users."""
    db = get_db()
    try:
        today = date.today()
        for user_pin in USER_PINS:
            holdings = db.table("user_portfolios").select("*").eq("user_pin", user_pin).execute()
            if not holdings.data:
                continue

            total_invested = sum(float(h.get("invested_value", 0) or 0) for h in holdings.data)
            total_current = sum(float(h.get("current_value", 0) or 0) for h in holdings.data)
            total_pnl = total_current - total_invested
            total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

            db.table("portfolio_snapshots").insert({
                "user_pin": user_pin,
                "snapshot_date": str(today),
                "holdings": [{
                    "symbol": h["symbol"], "qty": h.get("qty"),
                    "avg_price": float(h.get("avg_price", 0)),
                    "current_price": float(h.get("current_price", 0)),
                    "pnl": float(h.get("pnl", 0) or 0),
                } for h in holdings.data],
                "total_invested": total_invested,
                "total_current": total_current,
                "total_pnl": total_pnl,
                "total_pnl_pct": round(total_pnl_pct, 2),
            }).execute()

        logger.info(f"[4:05 PM] Portfolio snapshots saved for {len(USER_PINS)} users")
    except Exception as e:
        logger.error(f"Portfolio snapshot failed: {e}")


async def job_f_scanner():
    """4:10 PM — Run F1/F2/F3 scanner."""
    from app.services.scanners.fundamental import run_f_scanner

    db = get_db()
    try:
        result = run_f_scanner(db)
        logger.info(f"[4:10 PM] F-Scanner completed: {result}")
    except Exception as e:
        logger.error(f"F-Scanner failed: {e}")


async def job_generate_actions():
    """4:15 PM — Generate action items from scan results."""
    from app.services.action_engine import generate_actions_from_scan

    db = get_db()
    try:
        count = generate_actions_from_scan(db)
        logger.info(f"[4:15 PM] Generated {count} action items")
    except Exception as e:
        logger.error(f"Action generation failed: {e}")


async def job_telegram_summary():
    """4:30 PM — Send daily summary via Telegram."""
    from app.services.telegram_service import send_daily_summary

    db = get_db()
    try:
        sent = await send_daily_summary(db)
        logger.info(f"[4:30 PM] Telegram daily summary sent to {sent} users")
    except Exception as e:
        logger.error(f"Telegram summary failed: {e}")


async def job_news_scrape():
    """3x daily — Scrape news from all sources."""
    from app.services.news_scorer import update_article_sentiments
    from app.services.news_scraper import scrape_all_sources

    db = get_db()
    try:
        count = await scrape_all_sources(db)
        scored = update_article_sentiments(db)
        logger.info(f"[News] Scraped {count} articles, scored {scored}")
    except Exception as e:
        logger.error(f"News scraping failed: {e}")


async def job_weekly_refresh():
    """Weekly Sunday 7:30 PM — Refresh instruments + fundamentals."""
    from app.services.fundamentals_service import refresh_all_fundamentals
    from app.services.instruments_service import refresh_instruments_from_nse

    db = get_db()
    try:
        inst_count = await refresh_instruments_from_nse(db)
        logger.info(f"[Weekly] Refreshed instruments: {inst_count} new stocks")

        fund_count = await refresh_all_fundamentals(db)
        logger.info(f"[Weekly] Refreshed fundamentals for {fund_count} stocks")
    except Exception as e:
        logger.error(f"Weekly refresh failed: {e}")


async def main():
    """Run the full daily pipeline (4:00–4:30 PM sequence)."""
    await job_daily_scan()
    await job_portfolio_snapshots()
    await job_f_scanner()
    await job_generate_actions()
    await job_telegram_summary()
    logger.info("Daily pipeline completed")


if __name__ == "__main__":
    import sys as _sys
    job = _sys.argv[1] if len(_sys.argv) > 1 else "daily"

    if job == "daily":
        asyncio.run(main())
    elif job == "news":
        asyncio.run(job_news_scrape())
    elif job == "weekly":
        asyncio.run(job_weekly_refresh())
    else:
        print(f"Unknown job: {job}. Use: daily, news, weekly")
