"""Financial Astrology service — reads Sarvatobhadra Chakra signals from sbc_* tables."""
import logging

from supabase import Client

logger = logging.getLogger(__name__)


def get_commodity_signals(db: Client) -> list[dict]:
    result = db.rpc("exec_sql", {
        "query": """
            SELECT commodity, prediction_date, signal, confidence,
                   reasoning, predicted_direction, created_at
            FROM sbc_daily_predictions
            ORDER BY prediction_date DESC, commodity
            LIMIT 50
        """
    }).execute()
    rows = result.data or []
    return [
        {
            "commodity": r["commodity"],
            "prediction_date": str(r["prediction_date"]),
            "signal": r["signal"],
            "confidence": float(r["confidence"]) if r.get("confidence") else 0,
            "reasoning": r.get("reasoning", ""),
            "predicted_direction": r.get("predicted_direction", ""),
        }
        for r in rows
    ]


def get_planet_positions(db: Client) -> list[dict]:
    result = db.rpc("exec_sql", {
        "query": """
            SELECT planet_name, position_date, rashi, nakshatra, degree, is_retrograde
            FROM sbc_planet_positions
            ORDER BY position_date DESC, planet_name
            LIMIT 50
        """
    }).execute()
    rows = result.data or []
    return [
        {
            "planet": r["planet_name"],
            "date": str(r["position_date"]),
            "rashi": r["rashi"],
            "nakshatra": r["nakshatra"],
            "degree": float(r["degree"]) if r.get("degree") else 0,
            "is_retrograde": r.get("is_retrograde"),
        }
        for r in rows
    ]


def get_prediction_accuracy(db: Client) -> list[dict]:
    result = db.rpc("exec_sql", {
        "query": """
            SELECT commodity, total_predictions, correct_predictions, accuracy_pct,
                   avg_confidence, last_updated
            FROM sbc_prediction_accuracy
            ORDER BY accuracy_pct DESC
        """
    }).execute()
    rows = result.data or []
    return [
        {
            "commodity": r["commodity"],
            "total": r["total_predictions"],
            "correct": r["correct_predictions"],
            "accuracy_pct": float(r["accuracy_pct"]) if r.get("accuracy_pct") else 0,
            "avg_confidence": float(r["avg_confidence"]) if r.get("avg_confidence") else 0,
        }
        for r in rows
    ]
