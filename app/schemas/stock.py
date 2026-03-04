from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class NseStockOut(BaseModel):
    symbol: str
    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    market_cap: Decimal | None = None
    isin: str | None = None
    series: str | None = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class StockFundamentalsOut(BaseModel):
    symbol: str
    pe: Decimal | None = None
    pb: Decimal | None = None
    roe: Decimal | None = None
    roce: Decimal | None = None
    debt_equity: Decimal | None = None
    market_cap: Decimal | None = None
    dividend_yield: Decimal | None = None
    eps: Decimal | None = None
    book_value: Decimal | None = None
    face_value: Decimal | None = None
    promoter_holding: Decimal | None = None
    current_price: Decimal = 0
    sales_growth_5y: Decimal = 0
    profit_growth_5y: Decimal = 0
    fii_holding: Decimal = 0
    rsi: Decimal = 0
    dma_50: Decimal = 0
    dma_200: Decimal = 0
    f1_status: str | None = None
    f2_status: str | None = None
    f3_status: str | None = None
    f1_score: Decimal = 0
    f2_score: Decimal = 0
    f3_score: Decimal = 0
    overall_score: Decimal = 0
    last_calculated_at: datetime | None = None

    model_config = {"from_attributes": True}
