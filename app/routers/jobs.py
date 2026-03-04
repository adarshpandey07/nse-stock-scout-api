from datetime import date

from fastapi import APIRouter, BackgroundTasks, Query

from app.dependencies import AdminUser, DB
from app.schemas.results import FetchRunOut
from app.services.bhavcopy import fetch_bhavcopy, rebuild_history
from app.services.scanners import run_tight_scanner, run_vcp_scanner
from app.utils import last_trading_day

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/fetch-bhavcopy", response_model=FetchRunOut)
async def trigger_fetch(
    db: DB,
    _user: AdminUser,
    target_date: date = Query(default=None),
):
    """Manually trigger bhavcopy fetch for a date (default: last trading day)."""
    if target_date is None:
        target_date = last_trading_day()
    run = await fetch_bhavcopy(db, target_date)
    return run


@router.post("/run-scan")
async def trigger_scan(
    db: DB,
    _user: AdminUser,
    scanner: int = Query(1, ge=1, le=2),
    scan_date: date = Query(default=None),
):
    """Run a scanner on existing data."""
    if scan_date is None:
        scan_date = last_trading_day()

    if scanner == 1:
        count = run_vcp_scanner(db, scan_date)
        return {"scanner": "VCP Daily", "scan_date": str(scan_date), "results": count}
    else:
        count = run_tight_scanner(db, scan_date)
        return {"scanner": "Tight Consolidation", "scan_date": str(scan_date), "results": count}


@router.post("/run-all")
async def trigger_all(
    db: DB,
    _user: AdminUser,
    scan_date: date = Query(default=None),
):
    """Fetch bhavcopy + run both scanners."""
    if scan_date is None:
        scan_date = last_trading_day()

    run = await fetch_bhavcopy(db, scan_date)
    vcp_count = run_vcp_scanner(db, scan_date)
    tight_count = run_tight_scanner(db, scan_date)

    return {
        "fetch": {"status": run["status"], "inserted": run.get("inserted_count", 0)},
        "vcp": {"results": vcp_count},
        "tight": {"results": tight_count},
        "scan_date": str(scan_date),
    }


@router.post("/rebuild-history")
async def trigger_rebuild(
    db: DB,
    _user: AdminUser,
    start_date: date = Query(...),
    end_date: date = Query(...),
):
    """Fetch bhavcopy for a range of dates to build history."""
    runs = await rebuild_history(db, start_date, end_date)
    return {
        "dates_attempted": len(runs),
        "completed": sum(1 for r in runs if r.get("status") == "completed"),
        "failed": sum(1 for r in runs if r.get("status") == "failed"),
    }
