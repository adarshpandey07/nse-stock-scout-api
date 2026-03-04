from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class WatchlistItemOut(BaseModel):
    id: str
    user_pin: str
    symbol: str
    watchlist_type: str
    notes: str
    f1_status: bool
    f2_status: bool
    f3_status: bool
    news_score: int
    score: Decimal
    sector: str
    close_price: Decimal
    added_at: datetime

    model_config = {"from_attributes": True}


class WatchlistItemCreate(BaseModel):
    user_pin: str
    symbol: str
    watchlist_type: str = "long_term"
    notes: str = ""
