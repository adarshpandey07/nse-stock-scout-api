from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class WatchlistItemOut(BaseModel):
    id: str
    user_pin: str
    symbol: str
    watchlist_type: str | None = None
    notes: str | None = None
    f1_status: bool | None = None
    f2_status: bool | None = None
    f3_status: bool | None = None
    news_score: int | None = None
    score: Decimal | None = None
    sector: str | None = None
    close_price: Decimal | None = None
    added_at: datetime | None = None

    model_config = {"from_attributes": True}


class WatchlistItemCreate(BaseModel):
    user_pin: str
    symbol: str
    watchlist_type: str = "long_term"
    notes: str = ""
