from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel


class FCriteriaOut(BaseModel):
    id: str
    criteria_group: str
    condition_name: str
    field_name: str
    operator: str
    value: Decimal
    description: str
    enabled: bool
    sort_order: int

    model_config = {"from_attributes": True}


class FCriteriaCreate(BaseModel):
    condition_name: str
    field_name: str
    operator: str = ">"
    value: Decimal = 0
    description: str = ""
    enabled: bool = True
    sort_order: int = 0


class FCriteriaUpdate(BaseModel):
    condition_name: str | None = None
    field_name: str | None = None
    operator: str | None = None
    value: Decimal | None = None
    description: str | None = None
    enabled: bool | None = None
    sort_order: int | None = None


class FScanRunOut(BaseModel):
    id: str
    run_date: date
    total_stocks: int
    f1_pass: int
    f2_pass: int
    f3_pass: int
    all_pass: int
    results: list
    created_at: datetime

    model_config = {"from_attributes": True}
