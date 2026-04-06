from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.dependencies import AdminUser, CurrentUser, DB
from app.schemas.fundamental import FCriteriaCreate, FCriteriaOut, FCriteriaUpdate, FScanRunOut
from app.services.scanners.fundamental import run_f_scanner

router = APIRouter(prefix="/f-scanner", tags=["f-scanner"])


@router.get("/groups")
def get_criteria_groups(db: DB, _user: CurrentUser):
    criteria = db.table("f_criteria_config").select("*").order("criteria_group").order("sort_order").execute().data
    groups = {"F1": [], "F2": [], "F3": []}
    for c in criteria:
        grp = c.get("criteria_group", "")
        if grp not in groups:
            groups[grp] = []
        groups[grp].append(c)
    return groups


@router.post("/groups/{group_key}/criteria", response_model=FCriteriaOut)
def add_criteria(group_key: str, req: FCriteriaCreate, db: DB, _user: AdminUser):
    if group_key not in ("F1", "F2", "F3"):
        raise HTTPException(status_code=400, detail="group_key must be F1, F2, or F3")
    row = {
        "criteria_group": group_key,
        "condition_name": req.condition_name,
        "field_name": req.field_name,
        "operator": req.operator,
        "value": req.value,
        "description": req.description,
        "enabled": req.enabled,
        "sort_order": req.sort_order,
    }
    result = db.table("f_criteria_config").insert(row).execute()
    return result.data[0] if result.data else row


@router.put("/criteria/{criteria_id}", response_model=FCriteriaOut)
def update_criteria(criteria_id: str, req: FCriteriaUpdate, db: DB, _user: AdminUser):
    existing = db.table("f_criteria_config").select("id").eq("id", criteria_id).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Criteria not found")
    updates = req.model_dump(exclude_unset=True)
    result = db.table("f_criteria_config").update(updates).eq("id", criteria_id).execute()
    return result.data[0] if result.data else {}


@router.delete("/criteria/{criteria_id}")
def delete_criteria(criteria_id: str, db: DB, _user: AdminUser):
    existing = db.table("f_criteria_config").select("id").eq("id", criteria_id).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Criteria not found")
    db.table("f_criteria_config").delete().eq("id", criteria_id).execute()
    return {"status": "deleted"}


@router.post("/run", response_model=FScanRunOut)
def trigger_f_scan(db: DB, _user: AdminUser, scan_date: date = Query(None)):
    return run_f_scanner(db, scan_date)


@router.get("/runs", response_model=list[FScanRunOut])
def list_runs(db: DB, _user: CurrentUser, limit: int = Query(20, le=50)):
    return db.table("f_scan_runs").select("*").order("created_at", desc=True).limit(limit).execute().data


@router.get("/runs/{run_id}", response_model=FScanRunOut)
def get_run(run_id: str, db: DB, _user: CurrentUser):
    result = db.table("f_scan_runs").select("*").eq("id", run_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Run not found")
    return result.data[0]
