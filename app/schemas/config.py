import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ConfigOut(BaseModel):
    id: uuid.UUID
    config_data: dict[str, Any]
    updated_by: uuid.UUID | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConfigUpdate(BaseModel):
    config_data: dict[str, Any]
