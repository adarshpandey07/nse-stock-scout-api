from fastapi import APIRouter, Query

from app.dependencies import CurrentUser, DB
from app.schemas.trade import TradeOut
from app.services.trade_service import get_trades

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("/", response_model=list[TradeOut])
def list_trades(
    db: DB, _user: CurrentUser,
    user_pin: str = Query(...),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    return get_trades(db, user_pin, limit, offset)
