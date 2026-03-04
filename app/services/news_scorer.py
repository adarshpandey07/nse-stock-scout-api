"""News sentiment scoring — computes pointer score per stock (0-10)."""
import logging
from datetime import datetime, timedelta, timezone

from supabase import Client

logger = logging.getLogger(__name__)

SENTIMENT_WEIGHTS = {"bullish": 1.0, "neutral": 0.5, "bearish": 0.0}


def score_article_sentiment(headline: str, summary: str) -> str:
    text = (headline + " " + summary).lower()
    positive_words = [
        "surge", "rally", "profit", "growth", "buy", "upgrade", "bull",
        "outperform", "strong", "beat", "record", "high", "gain", "rise",
        "positive", "boost", "expand", "dividend", "breakout",
    ]
    negative_words = [
        "fall", "drop", "loss", "sell", "downgrade", "bear", "crash",
        "weak", "miss", "decline", "low", "slump", "negative", "cut",
        "fraud", "scam", "warning", "default", "debt",
    ]
    pos_count = sum(1 for w in positive_words if w in text)
    neg_count = sum(1 for w in negative_words if w in text)
    if pos_count > neg_count:
        return "bullish"
    elif neg_count > pos_count:
        return "bearish"
    return "neutral"


def update_article_sentiments(db: Client, symbol: str | None = None) -> int:
    q = db.table("stock_news").select("*").eq("sentiment", "neutral")
    if symbol:
        q = q.eq("symbol", symbol)
    articles = q.execute().data

    for article in articles:
        sentiment = score_article_sentiment(article["headline"], article.get("summary", ""))
        news_score = 8 if sentiment == "bullish" else (2 if sentiment == "bearish" else 5)
        db.table("stock_news").update({
            "sentiment": sentiment,
            "news_score": news_score,
        }).eq("id", article["id"]).execute()

    return len(articles)


def compute_pointer_score(db: Client, symbol: str) -> dict | None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    articles = (
        db.table("stock_news")
        .select("*")
        .eq("symbol", symbol)
        .gte("created_at", cutoff)
        .execute()
        .data
    )
    if not articles:
        return None

    sources = {s["id"]: s.get("credibility_score", 5) for s in db.table("news_sources").select("id,credibility_score").execute().data}

    total_weight = 0
    weighted_score = 0
    pos = neg = neu = 0

    for a in articles:
        credibility = sources.get(a.get("source_id"), 5)
        sentiment_val = SENTIMENT_WEIGHTS.get(a.get("sentiment", "neutral"), 0.5)
        score = sentiment_val * credibility
        weighted_score += score
        total_weight += credibility
        if a.get("sentiment") == "bullish":
            pos += 1
        elif a.get("sentiment") == "bearish":
            neg += 1
        else:
            neu += 1

    pointer = round((weighted_score / total_weight) * 10, 2) if total_weight > 0 else 5.0
    pointer = min(10, max(0, pointer))

    row = {
        "symbol": symbol,
        "pointer_score": pointer,
        "article_count": len(articles),
        "positive_count": pos,
        "negative_count": neg,
        "neutral_count": neu,
        "last_calculated_at": datetime.now(timezone.utc).isoformat(),
    }

    existing = db.table("news_pointer_scores").select("id").eq("symbol", symbol).limit(1).execute()
    if existing.data:
        result = db.table("news_pointer_scores").update(row).eq("symbol", symbol).execute()
    else:
        result = db.table("news_pointer_scores").insert(row).execute()

    return result.data[0] if result.data else row
