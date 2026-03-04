"""Financial Astrology service — reads Sarvatobhadra Chakra signals from sbc_* tables."""
import logging

from supabase import Client

logger = logging.getLogger(__name__)


def get_commodity_signals(db: Client) -> list[dict]:
    result = (
        db.table("sbc_daily_predictions")
        .select("commodity_name, date, prediction, total_shubh_score, total_krur_score, net_score, reasoning, created_at")
        .order("date", desc=True)
        .order("commodity_name")
        .limit(50)
        .execute()
    )
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
    result = (
        db.table("sbc_planet_positions")
        .select("date, graha_id, rashi_id, nakshatra_id, longitude_degrees, is_vakri")
        .order("date", desc=True)
        .limit(50)
        .execute()
    )
    rows = result.data or []

    # Fetch lookup tables for names
    grahas = {g["id"]: g["name_en"] for g in db.table("sbc_grahas").select("id, name_en").execute().data or []}
    rashis = {r["id"]: r["name_en"] for r in db.table("sbc_rashis").select("id, name_en").execute().data or []}
    nakshatras = {n["id"]: n["name_en"] for n in db.table("sbc_nakshatras").select("id, name_en").execute().data or []}

    return [
        {
            "planet": grahas.get(r["graha_id"], "Unknown"),
            "date": str(r["date"]),
            "rashi": rashis.get(r.get("rashi_id"), ""),
            "nakshatra": nakshatras.get(r.get("nakshatra_id"), ""),
            "degree": float(r["longitude_degrees"]) if r.get("longitude_degrees") else 0,
            "is_retrograde": r.get("is_vakri", False),
        }
        for r in rows
    ]


def get_prediction_accuracy(db: Client) -> list[dict]:
    result = (
        db.table("sbc_prediction_accuracy")
        .select("date, commodity_id, predicted_direction, actual_direction, is_correct, score_deviation, actual_close, previous_close")
        .order("date", desc=True)
        .limit(100)
        .execute()
    )
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
