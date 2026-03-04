from fastapi import APIRouter, Query

from app.dependencies import DB, CurrentUser
from app.schemas.activity import ActivityOut

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("", response_model=list[ActivityOut])
def get_activity(
    db: DB,
    _user: CurrentUser,
    event_type: str | None = Query(None),
    entity_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    q = db.table("activity_logs").select("*")
    if event_type:
        q = q.eq("event_type", event_type)
    if entity_type:
        q = q.eq("entity_type", entity_type)
    return q.order("created_at", desc=True).limit(limit).execute().data
