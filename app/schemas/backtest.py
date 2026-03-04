from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel


class BacktestRequest(BaseModel):
    user_pin: str
    date_from: date
    date_to: date
    strategy: str = "vcp"  # vcp, tight, f_scanner
    config: dict = {}


class BacktestRunOut(BaseModel):
    id: str
    user_pin: str
    date_from: date
    date_to: date
    strategy: str
    criteria_used: dict
    result_json: dict
    total_trades: int
    winning_trades: int
    pnl: Decimal
    pnl_pct: Decimal
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
