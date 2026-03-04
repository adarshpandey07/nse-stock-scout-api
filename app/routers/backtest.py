from fastapi import APIRouter, HTTPException, Query

from app.dependencies import CurrentUser, DB
from app.schemas.backtest import BacktestRequest, BacktestRunOut
from app.services.backtest_service import run_backtest

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/run", response_model=BacktestRunOut)
def trigger_backtest(req: BacktestRequest, db: DB, _user: CurrentUser):
    return run_backtest(db, req.user_pin, req.date_from, req.date_to, req.strategy, req.config)


@router.get("/runs", response_model=list[BacktestRunOut])
def list_runs(db: DB, _user: CurrentUser, user_pin: str = Query(...), limit: int = Query(20, le=50)):
    return (
        db.table("backtest_runs")
        .select("*")
        .eq("user_pin", user_pin)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )


@router.get("/runs/{run_id}", response_model=BacktestRunOut)
def get_run(run_id: str, db: DB, _user: CurrentUser):
    result = db.table("backtest_runs").select("*").eq("id", run_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return result.data[0]
