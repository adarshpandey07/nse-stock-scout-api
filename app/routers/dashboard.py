from fastapi import APIRouter, Query

from app.dependencies import CurrentUser, DB
from app.services.dashboard_service import get_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(db: DB, _user: CurrentUser, user_pin: str = Query(...)):
    return get_dashboard_summary(db, user_pin)
