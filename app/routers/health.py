from fastapi import APIRouter

from app.dependencies import DB
from app.utils import last_trading_day, today_ist

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.get("/data-status")
def data_status(db: DB):
    """Check freshness of daily_bars, scan_results, and fundamentals."""
    expected = last_trading_day()

    latest_bar = (
        db.table("daily_bars")
        .select("date")
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    latest_bar_date = latest_bar.data[0]["date"] if latest_bar.data else None

    latest_scan = (
        db.table("scan_results")
        .select("scan_date")
        .order("scan_date", desc=True)
        .limit(1)
        .execute()
    )
    latest_scan_date = latest_scan.data[0]["scan_date"] if latest_scan.data else None

    bar_count = db.table("daily_bars").select("symbol", count="exact").execute()
    stock_count = db.table("nse_stocks").select("symbol", count="exact").eq("is_active", True).execute()

    is_fresh = latest_bar_date is not None and latest_bar_date >= str(expected)

    return {
        "today_ist": str(today_ist()),
        "expected_trading_day": str(expected),
        "latest_bar_date": latest_bar_date,
        "latest_scan_date": latest_scan_date,
        "total_bars": bar_count.count or 0,
        "total_stocks": stock_count.count or 0,
        "is_data_fresh": is_fresh,
        "status": "fresh" if is_fresh else "STALE",
    }
