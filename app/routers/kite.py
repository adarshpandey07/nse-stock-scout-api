from fastapi import APIRouter, HTTPException, Query

from app.dependencies import CurrentUser, DB
from app.schemas.kite import (
    HoldingOut, KiteAccountOut, KiteCallbackRequest, KiteCredentialsRequest,
    MarginOut, OrderRequest, PositionOut,
)
from app.services import kite_service

router = APIRouter(prefix="/kite", tags=["kite"])


@router.post("/credentials", response_model=KiteAccountOut)
def save_kite_credentials(req: KiteCredentialsRequest, db: DB, _user: CurrentUser):
    try:
        acct = kite_service.save_credentials(db, req.user_pin, req.api_key, req.api_secret)
        return acct
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/login-url")
def get_login_url(db: DB, _user: CurrentUser, user_pin: str = Query(...)):
    try:
        url = kite_service.get_login_url(db, user_pin)
        return {"login_url": url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/callback", response_model=KiteAccountOut)
def kite_callback(req: KiteCallbackRequest, db: DB, _user: CurrentUser):
    try:
        acct = kite_service.handle_callback(db, req.user_pin, req.request_token)
        return acct
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/portfolio", response_model=list[HoldingOut])
def get_portfolio(db: DB, _user: CurrentUser, user_pin: str = Query(...)):
    try:
        return kite_service.get_holdings(db, user_pin)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/positions", response_model=list[PositionOut])
def get_positions(db: DB, _user: CurrentUser, user_pin: str = Query(...)):
    try:
        return kite_service.get_positions(db, user_pin)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/margins", response_model=MarginOut)
def get_margins(db: DB, _user: CurrentUser, user_pin: str = Query(...)):
    try:
        return kite_service.get_margins(db, user_pin)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/place-order")
def place_order(req: OrderRequest, db: DB, _user: CurrentUser):
    try:
        return kite_service.place_order(
            db, req.user_pin, req.symbol, req.exchange,
            req.transaction_type, req.quantity, req.order_type,
            req.price, req.product,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
