from datetime import datetime
from pydantic import BaseModel


class KiteAccountOut(BaseModel):
    user_pin: str
    user_name: str
    api_key: str
    is_connected: bool
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class KiteCallbackRequest(BaseModel):
    request_token: str
    user_pin: str


class KiteCredentialsRequest(BaseModel):
    user_pin: str
    api_key: str
    api_secret: str


class OrderRequest(BaseModel):
    user_pin: str
    symbol: str
    exchange: str = "NSE"
    transaction_type: str  # BUY / SELL
    quantity: int
    order_type: str = "MARKET"  # MARKET / LIMIT
    price: float | None = None
    product: str = "CNC"  # CNC / MIS / NRML


class HoldingOut(BaseModel):
    tradingsymbol: str
    exchange: str
    quantity: int
    average_price: float
    last_price: float
    pnl: float


class PositionOut(BaseModel):
    tradingsymbol: str
    exchange: str
    quantity: int
    average_price: float
    last_price: float
    pnl: float
    product: str


class MarginOut(BaseModel):
    available_cash: float
    used_margin: float
    available_margin: float
