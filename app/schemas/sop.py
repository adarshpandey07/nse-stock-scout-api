import uuid
from datetime import datetime

from pydantic import BaseModel


class SopOut(BaseModel):
    id: int
    slug: str
    title: str
    content_md: str
    updated_by: uuid.UUID | None
    updated_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class SopCreate(BaseModel):
    slug: str
    title: str
    content_md: str = ""


class SopUpdate(BaseModel):
    title: str | None = None
    content_md: str | None = None
