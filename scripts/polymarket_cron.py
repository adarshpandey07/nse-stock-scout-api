"""Polymarket Scanner Cron Jobs.

Run as: python -m scripts.polymarket_cron

Schedule:
  Every 10s:  Arb scanner (tight loop)
  Every 5m:   News reaction scanner
  Every 30m:  AI mispricing scanner
  Every 1h:   Market data sync
  Every 6h:   Settlement check
  Daily 11PM: P&L snapshot
"""

import asyncio
import logging
import time

from app.database import get_db
from app.services.polymarket.market_service import refresh_prices, sync_markets
from app.services.polymarket.position_service import take_snapshot
from app.services.polymarket.scanners import (
    run_arb_scanner,
    run_cross_arb_scanner,
    run_mispricing_scanner,
    run_news_reaction_scanner,
)
from app.services.polymarket.settlement_service import run_settlement

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s: %(message)s")
logger = logging.getLogger("polymarket_cron")

# Intervals in seconds
ARB_INTERVAL = 10
NEWS_INTERVAL = 300       # 5 minutes
MISPRICING_INTERVAL = 1800  # 30 minutes
SYNC_INTERVAL = 3600      # 1 hour
SETTLE_INTERVAL = 21600   # 6 hours
SNAPSHOT_INTERVAL = 86400  # 24 hours


async def arb_loop(db):
    """Run arb scanner every 10 seconds."""
    while True:
        try:
            count = run_arb_scanner(db)
            if count > 0:
                logger.info(f"Arb scanner: {count} opportunities found")
        except Exception as e:
            logger.error(f"Arb scanner error: {e}")
        await asyncio.sleep(ARB_INTERVAL)


async def news_loop(db):
    """Run news reaction scanner every 5 minutes."""
    while True:
        try:
            count = await run_news_reaction_scanner(db)
            if count > 0:
                logger.info(f"News scanner: {count} signals")
        except Exception as e:
            logger.error(f"News scanner error: {e}")
        await asyncio.sleep(NEWS_INTERVAL)


async def mispricing_loop(db):
    """Run AI mispricing scanner every 30 minutes."""
    while True:
        try:
            count = await run_mispricing_scanner(db)
            if count > 0:
                logger.info(f"Mispricing scanner: {count} signals")
        except Exception as e:
            logger.error(f"Mispricing scanner error: {e}")
        await asyncio.sleep(MISPRICING_INTERVAL)


async def sync_loop(db):
    """Sync market data every hour."""
    while True:
        try:
            count = await sync_markets(db)
            logger.info(f"Market sync: {count} markets")
            await refresh_prices(db)
        except Exception as e:
            logger.error(f"Market sync error: {e}")
        await asyncio.sleep(SYNC_INTERVAL)


async def settle_loop(db):
    """Check settlements every 6 hours."""
    while True:
        try:
            count = await run_settlement(db)
            if count > 0:
                logger.info(f"Settlement: {count} positions settled")
        except Exception as e:
            logger.error(f"Settlement error: {e}")
        await asyncio.sleep(SETTLE_INTERVAL)


async def snapshot_loop(db):
    """Take P&L snapshots daily."""
    while True:
        try:
            # Get all users with pm_config
            configs = db.table("pm_config").select("user_pin").execute().data
            for config in configs:
                take_snapshot(db, config["user_pin"])
            logger.info(f"P&L snapshots: {len(configs)} users")
        except Exception as e:
            logger.error(f"Snapshot error: {e}")
        await asyncio.sleep(SNAPSHOT_INTERVAL)


async def main():
    """Start all scanner loops concurrently."""
    db = get_db()
    logger.info("Starting Polymarket cron jobs...")

    # Initial market sync
    try:
        count = await sync_markets(db)
        logger.info(f"Initial sync: {count} markets loaded")
    except Exception as e:
        logger.error(f"Initial sync failed: {e}")

    # Run all loops concurrently
    await asyncio.gather(
        arb_loop(db),
        news_loop(db),
        mispricing_loop(db),
        sync_loop(db),
        settle_loop(db),
        snapshot_loop(db),
    )


if __name__ == "__main__":
    asyncio.run(main())
