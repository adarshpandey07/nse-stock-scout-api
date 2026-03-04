from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class ScanResultOut(BaseModel):
    id: str
    scan_date: date
    symbol: str
    scanner_type: int
    score: float
    company_name: str | None = None
    close_price: float | None = None
    range_pct: float | None = None
    volume_dry_ratio: float | None = None
    scanner_tag: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FetchRunOut(BaseModel):
    id: str
    run_date: date | None = None
    status: str | None = None
    total_symbols: int | None = None
    inserted_count: int | None = None
    skipped_count: int | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
