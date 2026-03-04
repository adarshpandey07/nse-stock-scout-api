from fastapi import APIRouter, Query

from app.dependencies import CurrentUser, DB
from app.services.portfolio_service import (
    brokerage_report, cashflow_report, pnl_report, portfolio_breakdown, stock_deep_dive,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/stock/{symbol}")
def analyze_stock(symbol: str, db: DB, _user: CurrentUser):
    return stock_deep_dive(db, symbol)


@router.get("/portfolio")
def analyze_portfolio(db: DB, _user: CurrentUser, user_pin: str = Query(...)):
    return portfolio_breakdown(db, user_pin)


@router.get("/pnl")
def get_pnl(db: DB, _user: CurrentUser, user_pin: str = Query(...), period: str = Query("daily")):
    return pnl_report(db, user_pin, period)


@router.get("/brokerage")
def get_brokerage(db: DB, _user: CurrentUser, user_pin: str = Query(...)):
    return brokerage_report(db, user_pin)


@router.get("/cashflow")
def get_cashflow(db: DB, _user: CurrentUser, user_pin: str = Query(...)):
    return cashflow_report(db, user_pin)
