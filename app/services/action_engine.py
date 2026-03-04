"""Action Centre engine — generates and manages actionable signals."""
import logging
from datetime import datetime, timezone

from supabase import Client

from app.services.activity import log_activity

logger = logging.getLogger(__name__)


def create_action(db: Client, action_type: str, symbol: str, message: str,
                  detail: str = "", priority: str = "medium", metadata: dict = None) -> dict:
    row = {
        "action_type": action_type,
        "symbol": symbol,
        "message": message,
        "detail": detail,
        "priority": priority,
        "metadata": metadata or {},
    }
    result = db.table("action_items").insert(row).execute()
    return result.data[0] if result.data else row


def decide_action(db: Client, action_id: str, decision: str, decided_by: str) -> dict:
    result = db.table("action_items").select("*").eq("id", action_id).limit(1).execute()
    if not result.data:
        raise ValueError("Action not found")

    updated = db.table("action_items").update({
        "status": decision,
        "decided_by": decided_by,
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", action_id).execute()

    return updated.data[0] if updated.data else result.data[0]


def generate_actions_from_scan(db: Client) -> int:
    # F-scanner: stocks passing all 3 groups
    f_stocks = (
        db.table("stock_fundamentals")
        .select("symbol,f1_score,f2_score,f3_score,overall_score")
        .eq("f1_status", True)
        .eq("f2_status", True)
        .eq("f3_status", True)
        .execute()
        .data
    )

    count = 0
    for stock in f_stocks:
        existing = (
            db.table("action_items")
            .select("id")
            .eq("symbol", stock["symbol"])
            .eq("action_type", "f_pass")
            .eq("status", "pending")
            .limit(1)
            .execute()
        )
        if existing.data:
            continue

        create_action(
            db, action_type="f_pass", symbol=stock["symbol"],
            message=f"{stock['symbol']} passes all F1/F2/F3 criteria",
            detail=f"F1: {stock['f1_score']}, F2: {stock['f2_score']}, F3: {stock['f3_score']}, Overall: {stock['overall_score']}",
            priority="high",
            metadata={"f1": stock["f1_score"], "f2": stock["f2_score"], "f3": stock["f3_score"]},
        )
        count += 1

    # News: stocks with pointer score > 8
    high_news = db.table("news_pointer_scores").select("symbol,pointer_score,article_count").gt("pointer_score", 8).execute().data
    for ns in high_news:
        existing = (
            db.table("action_items")
            .select("id")
            .eq("symbol", ns["symbol"])
            .eq("action_type", "news_alert")
            .eq("status", "pending")
            .limit(1)
            .execute()
        )
        if existing.data:
            continue

        create_action(
            db, action_type="news_alert", symbol=ns["symbol"],
            message=f"{ns['symbol']} has high news sentiment score: {ns['pointer_score']}",
            priority="medium",
            metadata={"pointer_score": ns["pointer_score"], "articles": ns["article_count"]},
        )
        count += 1

    log_activity(db, event_type="actions_generated", entity_type="action_items",
                 entity_id="auto", message=f"Generated {count} new action items",
                 status="completed", metadata_json={"count": count})
    return count
