import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.config import settings
from app.dependencies import AdminUser, DB
from app.database import get_db
from app.schemas.results import FetchRunOut
from app.services.bhavcopy import fetch_bhavcopy, rebuild_history
from app.services.scanners import run_tight_scanner, run_vcp_scanner, run_ipo_scanner
from app.utils import last_trading_day, today_ist, trading_days_between, _is_trading_day

logger = logging.getLogger(__name__)

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
    background_tasks: BackgroundTasks,
    scanner: int = Query(1, ge=1, le=3),
    scan_date: date = Query(default=None),
):
    """Run a scanner in background — returns immediately."""
    if scan_date is None:
        scan_date = last_trading_day()

    scanner_names = {1: "VCP Daily", 2: "Tight Consolidation", 3: "IPO Base"}
    scanner_fns = {1: run_vcp_scanner, 2: run_tight_scanner, 3: run_ipo_scanner}

    def _run():
        try:
            count = scanner_fns[scanner](db, scan_date)
            logger.info(f"Background scan {scanner} completed: {count} results")
        except Exception as e:
            logger.error(f"Background scan {scanner} failed: {e}")

    background_tasks.add_task(_run)
    return {
        "status": "started",
        "scanner": scanner_names[scanner],
        "scan_date": str(scan_date),
    }


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
    ipo_count = run_ipo_scanner(db, scan_date)

    return {
        "fetch": {"status": run["status"], "inserted": run.get("inserted_count", 0)},
        "vcp": {"results": vcp_count},
        "tight": {"results": tight_count},
        "ipo": {"results": ipo_count},
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


@router.post("/catch-up")
async def catch_up(db: DB, _user: AdminUser):
    """Auto-detect missing trading days since last fetch and backfill them all."""
    latest = (
        db.table("daily_bars")
        .select("date")
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    if not latest.data:
        return {"error": "No existing data. Use /rebuild-history with explicit dates."}

    last_date = date.fromisoformat(latest.data[0]["date"])
    target = last_trading_day()

    if last_date >= target:
        return {"status": "already_current", "latest": str(last_date), "target": str(target)}

    # Fetch all missing trading days
    missing_days = trading_days_between(last_date + timedelta(days=1), target)
    if not missing_days:
        return {"status": "already_current", "latest": str(last_date), "target": str(target)}

    results = []
    for d in missing_days:
        try:
            run = await fetch_bhavcopy(db, d)
            results.append({"date": str(d), "status": "ok", "inserted": run.get("inserted_count", 0)})
        except Exception as e:
            results.append({"date": str(d), "status": "failed", "error": str(e)[:200]})

    # Run scanners on the latest day
    vcp_count = run_vcp_scanner(db, target)
    tight_count = run_tight_scanner(db, target)
    ipo_count = run_ipo_scanner(db, target)

    return {
        "latest_before": str(last_date),
        "target": str(target),
        "days_fetched": len(results),
        "successful": sum(1 for r in results if r["status"] == "ok"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "vcp_results": vcp_count,
        "tight_results": tight_count,
        "ipo_results": ipo_count,
        "details": results,
    }


# ── Free Cron Endpoint (no JWT, protected by secret key) ──


@router.get("/cron/daily")
async def cron_daily(key: str = Query(...)):
    """Daily pipeline triggered by external free cron service.

    Protected by CRON_SECRET_KEY — no login needed.
    Set up cron-job.org to hit:
      GET https://nse-stock-scout-api.onrender.com/jobs/cron/daily?key=YOUR_SECRET
    """
    if key != settings.cron_secret_key:
        raise HTTPException(status_code=403, detail="Invalid cron key")

    today = today_ist()
    if not _is_trading_day(today):
        return {"status": "skipped", "reason": f"{today} is not a trading day"}

    db = get_db()
    target = last_trading_day()

    # Check if already fetched today
    latest = (
        db.table("daily_bars")
        .select("date")
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    if latest.data and latest.data[0]["date"] >= str(target):
        return {"status": "already_current", "date": str(target)}

    # Fetch bhavcopy + scanners
    try:
        run = await fetch_bhavcopy(db, target)
        vcp = run_vcp_scanner(db, target)
        tight = run_tight_scanner(db, target)
        ipo = run_ipo_scanner(db, target)

        logger.info(f"Cron daily completed: {run.get('inserted_count', 0)} bars, VCP={vcp}, Tight={tight}, IPO={ipo}")
        return {
            "status": "completed",
            "date": str(target),
            "inserted": run.get("inserted_count", 0),
            "vcp_results": vcp,
            "tight_results": tight,
            "ipo_results": ipo,
        }
    except Exception as e:
        logger.error(f"Cron daily failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)[:300])
