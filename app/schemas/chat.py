from datetime import datetime
from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    user_pin: str
    session_id: str | None = None
    message: str


class ChatMessageOut(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionOut(BaseModel):
    id: str
    user_pin: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
