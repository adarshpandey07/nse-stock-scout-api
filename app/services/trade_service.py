"""Trade history service."""
from supabase import Client


def get_user_trades(db: Client, user_pin: str, limit: int = 50, offset: int = 0) -> list[dict]:
    result = (
        db.table("user_trades")
        .select("*")
        .eq("user_pin", user_pin)
        .order("executed_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data


def get_trade_by_id(db: Client, trade_id: str) -> dict | None:
    result = db.table("user_trades").select("*").eq("id", trade_id).limit(1).execute()
    return result.data[0] if result.data else None
