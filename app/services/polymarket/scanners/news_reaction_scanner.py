"""Strategy 3: News Reaction Trading Scanner.

Monitors news, identifies impacted markets, estimates price movement before crowd reprices.
"""

import logging
from datetime import datetime, timedelta, timezone

from supabase import Client

from app.services.activity import log_activity
from app.services.polymarket.ai_analyst import analyze_news_impact
from app.services.polymarket.risk_manager import kelly_size

logger = logging.getLogger(__name__)

MIN_MAGNITUDE = 0.05  # 5% minimum expected price move


async def run_news_reaction_scanner(db: Client, bankroll: float = 500) -> int:
    """News Reaction Trading Scanner.

    1. Fetch recent news (last 30 minutes) from stock_news table + external
    2. Match news to Polymarket markets by keyword
    3. Claude analyzes impact
    4. If magnitude > 5% and speed='fast': generate time-limited signal

    Returns count of signals generated.
    """
    # Fetch recent news articles (last 30 min)
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    news_articles = (
        db.table("stock_news")
        .select("headline,summary,source_name")
        .gt("created_at", cutoff)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
        .data
    )

    if not news_articles:
        return 0

    # Get active markets for matching
    markets = (
        db.table("pm_markets")
        .select("condition_id,question,yes_price,tokens,volume_24h")
        .eq("active", True)
        .gt("volume_24h", 5000)
        .not_.is_("yes_price", "null")
        .execute()
        .data
    )

    if not markets:
        return 0

    signals_created = 0
    now = datetime.now(timezone.utc)

    for article in news_articles:
        headline = article.get("headline", "")
        summary = article.get("summary", "")

        # Simple keyword matching: find markets related to this news
        headline_lower = headline.lower()
        matched_markets = []
        for market in markets:
            question_lower = market.get("question", "").lower()
            # Check for word overlap (naive but effective)
            headline_words = set(w for w in headline_lower.split() if len(w) > 3)
            question_words = set(w for w in question_lower.split() if len(w) > 3)
            overlap = headline_words & question_words
            if len(overlap) >= 2:  # At least 2 significant words match
                matched_markets.append(market)

        for market in matched_markets[:3]:  # Max 3 markets per article
            condition_id = market["condition_id"]
            yes_price = float(market.get("yes_price", 0.5))

            # Check for existing signal
            existing = (
                db.table("pm_signals")
                .select("id")
                .eq("condition_id", condition_id)
                .eq("strategy", "news_reaction")
                .eq("status", "pending")
                .limit(1)
                .execute()
            )
            if existing.data:
                continue

            # Claude analyzes news impact
            impact = await analyze_news_impact(
                question=market["question"],
                news_headline=headline,
                news_body=summary,
                current_price=yes_price,
            )

            magnitude = float(impact.get("magnitude", 0))
            speed = impact.get("speed", "slow")
            direction = impact.get("direction", "neutral")

            if magnitude < MIN_MAGNITUDE or speed != "fast" or direction == "neutral":
                continue

            # Determine trade
            if direction == "up":
                signal_type = "buy_yes"
                target_price = yes_price
                estimated_prob = min(yes_price + magnitude, 0.95)
            else:
                signal_type = "buy_no"
                target_price = 1.0 - yes_price
                estimated_prob = min((1.0 - yes_price) + magnitude, 0.95)

            # Kelly sizing
            size_usd = kelly_size(
                estimated_prob=estimated_prob,
                market_price=target_price,
                bankroll=bankroll,
                fraction=0.25,
            )

            if size_usd < 1:
                continue

            # Get token ID
            target_outcome = "yes" if direction == "up" else "no"
            token_id = ""
            for t in market.get("tokens", []):
                if t.get("outcome", "").lower() == target_outcome:
                    token_id = t.get("token_id", "")
                    break

            # Signal expires in 30 minutes (news reaction is time-sensitive)
            expires_at = (now + timedelta(minutes=30)).isoformat()

            signal_row = {
                "condition_id": condition_id,
                "strategy": "news_reaction",
                "signal_type": signal_type,
                "token_id": token_id,
                "side": "BUY",
                "recommended_price": round(target_price, 4),
                "recommended_size": size_usd,
                "estimated_edge": round(magnitude * 100, 2),
                "ai_probability": round(estimated_prob, 4),
                "market_probability": yes_price,
                "confidence": "medium",
                "reasoning": impact.get("reasoning", ""),
                "news_context": headline,
                "status": "pending",
                "expires_at": expires_at,
            }
            sig_result = db.table("pm_signals").insert(signal_row).execute()
            signal_id = sig_result.data[0]["id"] if sig_result.data else None

            # Action centre
            action_row = {
                "action_type": "pm_news_reaction",
                "symbol": condition_id[:20],
                "message": f"News reaction: {headline[:60]} → {direction} {magnitude*100:.0f}% on {market['question'][:50]}",
                "detail": f"Speed: {speed}. {impact.get('reasoning', '')}",
                "priority": "critical" if magnitude > 0.15 else "high",
                "metadata": {
                    "signal_id": signal_id,
                    "headline": headline,
                    "direction": direction,
                    "magnitude": magnitude,
                    "speed": speed,
                },
            }
            action_result = db.table("action_centre").insert(action_row).execute()

            if signal_id and action_result.data:
                db.table("pm_signals").update({
                    "action_centre_id": action_result.data[0]["id"],
                }).eq("id", signal_id).execute()

            signals_created += 1

    log_activity(
        db, event_type="pm_news_scan", entity_type="polymarket",
        entity_id="news_scanner",
        message=f"News scanner: {signals_created} signals from {len(news_articles)} articles",
        status="completed",
        metadata_json={"signals": signals_created, "articles": len(news_articles)},
    )

    return signals_created
