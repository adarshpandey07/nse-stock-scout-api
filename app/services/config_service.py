import uuid
from datetime import datetime, timezone

from supabase import Client

DEFAULT_CONFIG = {
    "scanner_1": {
        "name": "VCP Daily",
        "enabled": True,
        "weights": {
            "sma_trend": 25,
            "atr_contraction": 25,
            "tightness": 25,
            "volume_dry": 25,
        },
        "min_score": 60,
    },
    "scanner_2": {
        "name": "Tight Consolidation",
        "enabled": True,
        "weights": {
            "range_tightness": 40,
            "volume_contraction": 30,
            "days_in_range": 30,
        },
        "lookback_days": 20,
        "max_range_pct": 10.0,
        "min_score": 50,
    },
    "fetch": {
        "min_close_price": 20,
        "min_avg_volume": 50000,
    },
}


def get_active_config(db: Client) -> dict:
    result = db.table("scanner_config").select("*").order("updated_at", desc=True).limit(1).execute()
    if result.data:
        return result.data[0]
    # Create default
    new = db.table("scanner_config").insert({"config_data": DEFAULT_CONFIG}).execute()
    return new.data[0] if new.data else {"config_data": DEFAULT_CONFIG}


def update_config(db: Client, config_data: dict, user_id: str) -> dict:
    config = get_active_config(db)
    result = db.table("scanner_config").update({
        "config_data": config_data,
        "updated_by": str(user_id),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", config["id"]).execute()
    return result.data[0] if result.data else config
