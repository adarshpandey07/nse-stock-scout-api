from datetime import datetime
from pydantic import BaseModel


class ActionItemOut(BaseModel):
    id: str
    action_type: str
    symbol: str
    message: str
    detail: str
    priority: str
    status: str
    decided_by: str | None
    decided_at: datetime | None
    meta_data: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class ActionDecideRequest(BaseModel):
    decision: str  # accepted, rejected, snoozed
    decided_by: str
