"""Strategy 2: AI Mispricing Detection Scanner.

Uses Claude Opus to estimate true probability vs market price.
If gap > 10% → generate trade signal with Kelly-sized position.
"""

import logging
from datetime import datetime, timezone

from supabase import Client

from app.services.activity import log_activity
from app.services.polymarket.ai_analyst import batch_analyze_markets
from app.services.polymarket.risk_manager import kelly_size

logger = logging.getLogger(__name__)

MIN_VOLUME = 10000  # Only scan markets with >$10k volume
MIN_EDGE = 0.10     # 10% minimum edge to generate signal
MIN_LIQUIDITY = 5000


async def run_mispricing_scanner(db: Client, bankroll: float = 500) -> int:
    """AI Mispricing Detection Scanner.

    1. Load active markets with volume > $10k
    2. Batch-analyze with Claude AI
    3. If |claude_prob - market_price| > 10%: generate signal
    4. Kelly-size the position

    Returns count of signals generated.
    """
    # Fetch eligible markets
    markets = (
        db.table("pm_markets")
        .select("condition_id,question,description,yes_price,no_price,end_date,volume_24h,liquidity,tokens")
        .eq("active", True)
        .gt("volume_24h", MIN_VOLUME)
        .gt("liquidity", MIN_LIQUIDITY)
        .not_.is_("yes_price", "null")
        .order("volume_24h", desc=True)
        .limit(30)  # Limit to top 30 by volume (Claude API costs)
        .execute()
        .data
    )

    if not markets:
        return 0

    # Batch analyze with Claude
    analyses = await batch_analyze_markets(markets)

    signals_created = 0
    now = datetime.now(timezone.utc).isoformat()

    for analysis in analyses:
        edge = analysis.get("edge", 0)
        abs_edge = abs(edge)
        confidence = analysis.get("confidence", "low")

        # Skip low-confidence or small-edge
        if abs_edge < MIN_EDGE or confidence == "low":
            continue

        condition_id = analysis["condition_id"]
        claude_prob = analysis["probability"]
        market_price = analysis["market_price"]

        # Check for existing pending signal
        existing = (
            db.table("pm_signals")
            .select("id")
            .eq("condition_id", condition_id)
            .eq("strategy", "mispricing")
            .eq("status", "pending")
            .limit(1)
            .execute()
        )
        if existing.data:
            continue

        # Determine trade direction
        if edge > 0:
            # Claude thinks YES is underpriced → buy YES
            side = "BUY"
            signal_type = "buy_yes"
            price = market_price
        else:
            # Claude thinks YES is overpriced → buy NO
            side = "BUY"
            signal_type = "buy_no"
            price = 1.0 - market_price  # NO price

        # Kelly position sizing
        size_usd = kelly_size(
            estimated_prob=claude_prob if edge > 0 else (1 - claude_prob),
            market_price=price,
            bankroll=bankroll,
            fraction=0.25,
        )

        if size_usd < 1:
            continue  # Too small

        # Get token ID
        market = db.table("pm_markets").select("tokens").eq("condition_id", condition_id).limit(1).execute()
        token_id = ""
        if market.data:
            target_outcome = "yes" if edge > 0 else "no"
            for t in market.data[0].get("tokens", []):
                if t.get("outcome", "").lower() == target_outcome:
                    token_id = t.get("token_id", "")
                    break

        signal_row = {
            "condition_id": condition_id,
            "strategy": "mispricing",
            "signal_type": signal_type,
            "token_id": token_id,
            "side": side,
            "recommended_price": round(price, 4),
            "recommended_size": size_usd,
            "estimated_edge": round(abs_edge * 100, 2),
            "ai_probability": claude_prob,
            "market_probability": market_price,
            "confidence": confidence,
            "reasoning": analysis.get("reasoning", ""),
            "status": "pending",
        }
        sig_result = db.table("pm_signals").insert(signal_row).execute()
        signal_id = sig_result.data[0]["id"] if sig_result.data else None

        # Action centre notification
        question = analysis.get("question", "")[:80]
        action_row = {
            "action_type": "pm_mispricing",
            "symbol": condition_id[:20],
            "message": f"AI mispricing: {question} — Claude {claude_prob*100:.0f}% vs market {market_price*100:.0f}%",
            "detail": analysis.get("reasoning", ""),
            "priority": "high" if abs_edge > 0.20 else "medium",
            "metadata": {
                "signal_id": signal_id,
                "claude_prob": claude_prob,
                "market_price": market_price,
                "edge": round(edge * 100, 2),
                "kelly_size_usd": size_usd,
                "confidence": confidence,
            },
        }
        action_result = db.table("action_centre").insert(action_row).execute()

        if signal_id and action_result.data:
            db.table("pm_signals").update({
                "action_centre_id": action_result.data[0]["id"],
            }).eq("id", signal_id).execute()

        signals_created += 1
        logger.info(
            f"Mispricing signal: {question} — Claude {claude_prob:.2f} vs market {market_price:.2f} "
            f"(edge {abs_edge*100:.1f}%, size ${size_usd})"
        )

    log_activity(
        db, event_type="pm_mispricing_scan", entity_type="polymarket",
        entity_id="mispricing_scanner",
        message=f"Mispricing scanner: {signals_created} signals from {len(markets)} markets",
        status="completed",
        metadata_json={"signals": signals_created, "markets_analyzed": len(analyses)},
    )

    return signals_created
