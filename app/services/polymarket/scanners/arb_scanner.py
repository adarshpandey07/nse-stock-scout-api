"""Strategy 1: Sum-to-One Arbitrage Scanner.

Finds markets where YES + NO price < $1.00 after fees → guaranteed profit.
"""

import logging
from datetime import datetime, timezone

from supabase import Client

from app.services.activity import log_activity

logger = logging.getLogger(__name__)

TAKER_FEE = 0.003  # 0.30% per side
# Need spread < 1.0 - (2 * taker_fee) to be profitable after buying both sides
PROFITABLE_THRESHOLD = 1.0 - (2 * TAKER_FEE)  # 0.994


def run_arb_scanner(db: Client) -> int:
    """Scan all active markets for sum-to-one arbitrage opportunities.

    Algorithm:
    1. Load active markets with both yes_price and no_price set
    2. For each: spread = yes_price + no_price
    3. If spread < 0.994 (profitable after 2x taker fee):
       - profit_per_share = 1.00 - spread - (2 * TAKER_FEE)
       - Create pm_signal with strategy='arb', signal_type='buy_both'
       - Create action_centre item

    Returns count of signals generated.
    """
    markets = (
        db.table("pm_markets")
        .select("condition_id,question,tokens,yes_price,no_price,spread,volume_24h,liquidity")
        .eq("active", True)
        .not_.is_("yes_price", "null")
        .not_.is_("no_price", "null")
        .execute()
        .data
    )

    if not markets:
        return 0

    signals_created = 0
    now = datetime.now(timezone.utc).isoformat()

    for market in markets:
        yes_price = float(market.get("yes_price", 0))
        no_price = float(market.get("no_price", 0))

        if yes_price <= 0 or no_price <= 0:
            continue

        spread = yes_price + no_price
        profit_per_share = 1.0 - spread - (2 * TAKER_FEE)

        if profit_per_share <= 0:
            continue

        # Profitable arbitrage found!
        condition_id = market["condition_id"]
        edge_pct = round(profit_per_share * 100, 2)

        # Check for existing pending signal (avoid duplicates)
        existing = (
            db.table("pm_signals")
            .select("id")
            .eq("condition_id", condition_id)
            .eq("strategy", "arb")
            .eq("status", "pending")
            .limit(1)
            .execute()
        )
        if existing.data:
            continue

        # Get token IDs
        tokens = market.get("tokens", [])
        yes_token = ""
        no_token = ""
        for t in tokens:
            if t.get("outcome", "").lower() == "yes":
                yes_token = t.get("token_id", "")
            elif t.get("outcome", "").lower() == "no":
                no_token = t.get("token_id", "")

        # Determine recommended size (limited by liquidity)
        liquidity = float(market.get("liquidity", 0))
        max_size = min(liquidity * 0.01, 50)  # Max 1% of liquidity or $50
        recommended_size = max(max_size, 1)  # At least $1

        # Create signal for YES side
        signal_row = {
            "condition_id": condition_id,
            "strategy": "arb",
            "signal_type": "buy_both",
            "token_id": yes_token,  # Primary token (YES side)
            "side": "BUY",
            "recommended_price": yes_price,
            "recommended_size": recommended_size,
            "estimated_edge": edge_pct,
            "market_probability": yes_price,
            "confidence": "high",
            "reasoning": (
                f"Arbitrage: YES ${yes_price:.3f} + NO ${no_price:.3f} = ${spread:.4f}. "
                f"Buy both sides for guaranteed ${profit_per_share:.4f}/share profit ({edge_pct}% edge) "
                f"after 2x {TAKER_FEE*100:.1f}% taker fees."
            ),
            "status": "pending",
        }
        sig_result = db.table("pm_signals").insert(signal_row).execute()
        signal_id = sig_result.data[0]["id"] if sig_result.data else None

        # Also create action_centre item (unified notification)
        action_row = {
            "action_type": "pm_arb",
            "symbol": condition_id[:20],
            "message": f"Arb opportunity: {market['question'][:80]} — {edge_pct}% edge",
            "detail": signal_row["reasoning"],
            "priority": "high" if edge_pct > 1.0 else "medium",
            "metadata": {
                "signal_id": signal_id,
                "yes_price": yes_price,
                "no_price": no_price,
                "spread": spread,
                "profit_per_share": profit_per_share,
                "edge_pct": edge_pct,
            },
        }
        action_result = db.table("action_centre").insert(action_row).execute()

        # Link action to signal
        if signal_id and action_result.data:
            db.table("pm_signals").update({
                "action_centre_id": action_result.data[0]["id"],
            }).eq("id", signal_id).execute()

        signals_created += 1
        logger.info(f"Arb signal: {market['question'][:60]} — {edge_pct}% edge")

    log_activity(
        db, event_type="pm_arb_scan", entity_type="polymarket",
        entity_id="arb_scanner",
        message=f"Arb scanner: {signals_created} opportunities from {len(markets)} markets",
        status="completed",
        metadata_json={"signals": signals_created, "markets_scanned": len(markets)},
    )

    return signals_created
