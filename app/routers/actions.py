from fastapi import APIRouter, HTTPException, Query

from app.dependencies import AdminUser, CurrentUser, DB
from app.schemas.action import ActionDecideRequest, ActionItemOut
from app.services.action_engine import decide_action, generate_actions_from_scan

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("/", response_model=list[ActionItemOut])
def list_actions(
    db: DB, _user: CurrentUser,
    status: str = Query(None),
    action_type: str = Query(None),
    symbol: str = Query(None),
    limit: int = Query(50, le=200),
):
    q = db.table("action_items").select("*").order("created_at", desc=True)
    if status:
        q = q.eq("status", status)
    if action_type:
        q = q.eq("action_type", action_type)
    if symbol:
        q = q.eq("symbol", symbol.upper())
    return q.limit(limit).execute().data


@router.get("/pending", response_model=list[ActionItemOut])
def pending_actions(db: DB, _user: CurrentUser):
    return (
        db.table("action_items")
        .select("*")
        .eq("status", "pending")
        .order("created_at", desc=True)
        .execute()
        .data
    )


@router.post("/{action_id}/decide", response_model=ActionItemOut)
def decide(action_id: str, req: ActionDecideRequest, db: DB, _user: CurrentUser):
    try:
        return decide_action(db, action_id, req.decision, req.decided_by)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/generate")
def trigger_generation(db: DB, _user: AdminUser):
    count = generate_actions_from_scan(db)
    return {"actions_generated": count}
