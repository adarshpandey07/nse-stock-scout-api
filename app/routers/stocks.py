from fastapi import APIRouter, HTTPException, Query

from app.dependencies import AdminUser, CurrentUser, DB
from app.schemas.stock import NseStockOut, StockFundamentalsOut
from app.services import fundamentals_service, instruments_service
from app.services.kite_service import _get_kite_account

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/", response_model=list[NseStockOut])
def list_stocks(
    db: DB, _user: CurrentUser,
    search: str = Query(""),
    sector: str = Query(""),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    return instruments_service.get_all_stocks(db, search, sector, limit, offset)


@router.get("/{symbol}", response_model=NseStockOut)
def get_stock(symbol: str, db: DB, _user: CurrentUser):
    stock = instruments_service.get_stock_by_symbol(db, symbol)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    return stock


@router.get("/{symbol}/fundamentals", response_model=StockFundamentalsOut)
def get_fundamentals(symbol: str, db: DB, _user: CurrentUser):
    fund = fundamentals_service.get_fundamentals(db, symbol)
    if not fund:
        raise HTTPException(status_code=404, detail=f"No fundamentals for {symbol}")
    return fund


@router.post("/refresh-instruments")
async def refresh_instruments(db: DB, _user: AdminUser, source: str = Query("nse"), user_pin: str = Query(None)):
    """Refresh NSE instrument list. source=nse (free) or kite (requires credentials)."""
    try:
        if source == "kite":
            if not user_pin:
                raise HTTPException(status_code=400, detail="user_pin required for Kite source")
            acct = _get_kite_account(db, user_pin)
            count = instruments_service.refresh_instruments_from_kite(db, acct.api_key, acct.access_token)
        else:
            count = await instruments_service.refresh_instruments_from_nse(db)
        return {"status": "ok", "new_instruments": count, "source": source}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh-fundamentals")
async def refresh_fundamentals(db: DB, _user: AdminUser, symbol: str = Query(None)):
    """Refresh fundamentals from Screener.in."""
    symbols = [symbol] if symbol else None
    count = await fundamentals_service.refresh_all_fundamentals(db, symbols)
    return {"status": "ok", "refreshed": count}
