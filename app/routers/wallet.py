from fastapi import APIRouter, HTTPException, Query

from app.dependencies import CurrentUser, DB
from app.schemas.wallet import WalletOut, WalletTxnOut, WalletTxnRequest
from app.services import wallet_service

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("/balance", response_model=WalletOut)
def get_balance(db: DB, _user: CurrentUser, user_pin: str = Query(...)):
    try:
        return wallet_service.get_wallet(db, user_pin)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/deposit", response_model=WalletTxnOut)
def deposit(req: WalletTxnRequest, db: DB, _user: CurrentUser):
    try:
        return wallet_service.deposit(db, req.user_pin, req.amount, req.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/withdraw", response_model=WalletTxnOut)
def withdraw(req: WalletTxnRequest, db: DB, _user: CurrentUser):
    try:
        return wallet_service.withdraw(db, req.user_pin, req.amount, req.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transactions", response_model=list[WalletTxnOut])
def list_transactions(
    db: DB, _user: CurrentUser,
    user_pin: str = Query(...),
    limit: int = Query(50, le=200),
):
    return wallet_service.get_transactions(db, user_pin, limit)
