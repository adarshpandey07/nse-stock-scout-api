from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class NewsSourceOut(BaseModel):
    id: str
    name: str
    url: str
    credibility_score: int
    scrape_frequency: str
    enabled: bool
    last_scraped_at: datetime | None = None

    model_config = {"from_attributes": True}


class NewsSourceCreate(BaseModel):
    name: str
    url: str
    credibility_score: int = 5
    scrape_frequency: str = "daily"
    enabled: bool = True


class StockNewsOut(BaseModel):
    id: str
    symbol: str | None
    headline: str
    summary: str
    source_name: str
    news_score: int
    url: str
    sentiment: str
    published_at: datetime

    model_config = {"from_attributes": True}


class NewsPointerScoreOut(BaseModel):
    symbol: str
    pointer_score: Decimal
    article_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    last_calculated_at: datetime

    model_config = {"from_attributes": True}
