from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel


class SuperstarInvestorOut(BaseModel):
    id: str
    name: str
    description: str
    image_url: str
    net_worth: str
    is_active: bool

    model_config = {"from_attributes": True}


class SuperstarInvestorCreate(BaseModel):
    name: str
    description: str = ""
    image_url: str = ""
    net_worth: str = ""


class SuperstarHoldingOut(BaseModel):
    id: str
    investor_id: str | None
    symbol: str
    qty: int
    value: Decimal
    change_type: str
    change_pct: Decimal
    reported_date: date | None
    quarter: str

    model_config = {"from_attributes": True}
