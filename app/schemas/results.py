from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class ScanResultOut(BaseModel):
    id: int
    scan_date: date
    symbol: str
    scanner_type: int
    score: float
    metrics_json: dict[str, Any] | None
    close_price: float | None = None
    volume: int | None = None
    change_pct: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FetchRunOut(BaseModel):
    id: int
    run_date: date
    status: str
    total_symbols: int | None
    inserted_count: int | None
    skipped_count: int | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
