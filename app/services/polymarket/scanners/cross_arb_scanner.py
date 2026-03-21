"""Strategy 4: Cross-Market Arbitrage Scanner (Polymarket vs Kalshi).

Skeleton implementation — requires Kalshi API integration (Phase 6).
"""

import logging

from supabase import Client

from app.services.activity import log_activity

logger = logging.getLogger(__name__)


async def run_cross_arb_scanner(db: Client) -> int:
    """Cross-Market Arbitrage Scanner — Polymarket vs Kalshi.

    Phase 6 implementation. Currently returns 0.

    Algorithm (when implemented):
    1. Maintain a curated list of events that exist on both platforms
    2. Poll Polymarket prices from pm_markets cache
    3. Poll Kalshi prices via their API
    4. If price gap > combined fees on both platforms:
       - Buy cheap side on one, sell expensive side on other
       - Create pm_signal with strategy='cross_arb'
    5. Execution window: typically 2-7 seconds

    Requires:
    - Kalshi API key and SDK
    - Event mapping between platforms
    - Sub-second execution infrastructure
    """
    log_activity(
        db, event_type="pm_cross_arb_scan", entity_type="polymarket",
        entity_id="cross_arb_scanner",
        message="Cross-arb scanner: not yet implemented (Phase 6)",
        status="skipped",
    )
    return 0
