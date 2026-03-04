"""Financial Astrology service — reads Sarvatobhadra Chakra signals from sbc_* tables."""
import logging

from supabase import Client

logger = logging.getLogger(__name__)


def get_commodity_signals(db: Client) -> list[dict]:
    result = db.rpc("exec_sql", {
        "query": """
            SELECT commodity_name, date, prediction,
                   total_shubh_score, total_krur_score, net_score,
                   reasoning, created_at
            FROM sbc_daily_predictions
            ORDER BY date DESC, commodity_name
            LIMIT 50
        """
    }).execute()
    rows = result.data or []
    return [
        {
            "commodity": r["commodity_name"],
            "prediction_date": str(r["date"]),
            "signal": r["prediction"],
            "confidence": float(r["net_score"]) if r.get("net_score") else 0,
            "reasoning": r.get("reasoning", ""),
            "predicted_direction": r["prediction"],
            "shubh_score": float(r["total_shubh_score"]) if r.get("total_shubh_score") else 0,
            "krur_score": float(r["total_krur_score"]) if r.get("total_krur_score") else 0,
        }
        for r in rows
    ]


def get_planet_positions(db: Client) -> list[dict]:
    result = db.rpc("exec_sql", {
        "query": """
            SELECT pp.date, g.name_en AS planet_name,
                   r.name_en AS rashi, n.name_en AS nakshatra,
                   pp.longitude_degrees, pp.is_vakri
            FROM sbc_planet_positions pp
            JOIN sbc_grahas g ON g.id = pp.graha_id
            LEFT JOIN sbc_rashis r ON r.id = pp.rashi_id
            LEFT JOIN sbc_nakshatras n ON n.id = pp.nakshatra_id
            ORDER BY pp.date DESC, g.name_en
            LIMIT 50
        """
    }).execute()
    rows = result.data or []
    return [
        {
            "planet": r["planet_name"],
            "date": str(r["date"]),
            "rashi": r.get("rashi", ""),
            "nakshatra": r.get("nakshatra", ""),
            "degree": float(r["longitude_degrees"]) if r.get("longitude_degrees") else 0,
            "is_retrograde": r.get("is_vakri", False),
        }
        for r in rows
    ]


def get_prediction_accuracy(db: Client) -> list[dict]:
    result = db.rpc("exec_sql", {
        "query": """
            SELECT pa.date, pa.commodity_id, pa.predicted_direction,
                   pa.actual_direction, pa.is_correct, pa.score_deviation,
                   pa.actual_close, pa.previous_close
            FROM sbc_prediction_accuracy pa
            ORDER BY pa.date DESC
            LIMIT 100
        """
    }).execute()
    rows = result.data or []
    return [
        {
            "date": str(r["date"]),
            "commodity_id": r["commodity_id"],
            "predicted_direction": r.get("predicted_direction", ""),
            "actual_direction": r.get("actual_direction", ""),
            "is_correct": r.get("is_correct", False),
            "score_deviation": float(r["score_deviation"]) if r.get("score_deviation") else 0,
            "actual_close": float(r["actual_close"]) if r.get("actual_close") else 0,
            "previous_close": float(r["previous_close"]) if r.get("previous_close") else 0,
        }
        for r in rows
    ]
