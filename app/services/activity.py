import uuid
from datetime import datetime, timezone

from supabase import Client


def log_activity(
    db: Client,
    event_type: str,
    message: str,
    actor_user_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata_json: dict | None = None,
    status: str | None = None,
) -> dict:
    row = {
        "event_type": event_type,
        "message": message,
        "status": status,
    }
    if entity_type:
        row["entity_type"] = entity_type
    if metadata_json:
        row["metadata_json"] = metadata_json
    if actor_user_id:
        row["actor_user_id"] = str(actor_user_id)

    try:
        result = db.table("activity_log").insert(row).execute()
        return result.data[0] if result.data else row
    except Exception:
        # Activity logging should never break the main operation
        return row
