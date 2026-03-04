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
        "entity_type": entity_type,
        "entity_id": entity_id,
        "metadata_json": metadata_json,
        "status": status,
    }
    if actor_user_id:
        row["actor_user_id"] = str(actor_user_id)

    result = db.table("activity_logs").insert(row).execute()
    return result.data[0] if result.data else row
