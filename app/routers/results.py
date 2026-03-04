from datetime import date

from fastapi import APIRouter, Query

from app.dependencies import DB, CurrentUser
from app.schemas.results import FetchRunOut, ScanResultOut
from app.utils import last_trading_day

router = APIRouter(prefix="/results", tags=["results"])


@router.get("/latest", response_model=list[ScanResultOut])
def get_latest_results(
    db: DB,
    _user: CurrentUser,
    scanner: int = Query(1, ge=1, le=2),
    limit: int = Query(50, ge=1, le=200),
):
    return (
        db.table("scan_results")
        .select("*")
        .eq("scanner_type", scanner)
        .order("scan_date", desc=True)
        .order("score", desc=True)
        .limit(limit)
        .execute()
        .data
    )


@router.get("/by-date", response_model=list[ScanResultOut])
def get_results_by_date(
    db: DB,
    _user: CurrentUser,
    scan_date: date = Query(default=None),
    scanner: int = Query(1, ge=1, le=2),
):
    if scan_date is None:
        scan_date = last_trading_day()
    return (
        db.table("scan_results")
        .select("*")
        .eq("scan_date", str(scan_date))
        .eq("scanner_type", scanner)
        .order("score", desc=True)
        .execute()
        .data
    )


@router.get("/symbol/{symbol}", response_model=list[ScanResultOut])
def get_results_by_symbol(
    symbol: str,
    db: DB,
    _user: CurrentUser,
    scanner: int = Query(None, ge=1, le=2),
    limit: int = Query(30, ge=1, le=100),
):
    q = db.table("scan_results").select("*").eq("symbol", symbol.upper())
    if scanner:
        q = q.eq("scanner_type", scanner)
    return q.order("scan_date", desc=True).limit(limit).execute().data


@router.get("/fetch-runs", response_model=list[FetchRunOut])
def get_data_fetch_runs(
    db: DB,
    _user: CurrentUser,
    limit: int = Query(20, ge=1, le=100),
):
    return (
        db.table("data_fetch_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )
