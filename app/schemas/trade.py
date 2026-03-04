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
    brokerage: Decimal | None = None
    stt: Decimal | None = None
    total: Decimal | None = None
    order_id: str | None = None
    status: str | None = None
    notes: str | None = None
    executed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
