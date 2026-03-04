import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ActivityOut(BaseModel):
    id: int
    event_type: str
    entity_type: str | None
    entity_id: str | None
    message: str
    actor_user_id: uuid.UUID | None
    metadata_json: dict[str, Any] | None
    status: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
