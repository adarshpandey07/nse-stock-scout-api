from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class TradeOut(BaseModel):
    id: str
    user_pin: str
    symbol: str
    side: str
    qty: int
    price: Decimal
    brokerage: Decimal
    stt: Decimal
    total: Decimal
    order_id: str
    status: str
    notes: str
    executed_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
