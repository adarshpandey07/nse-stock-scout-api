from pydantic import BaseModel


class TelegramConfigOut(BaseModel):
    user_pin: str | None
    chat_id: str
    enabled: bool

    model_config = {"from_attributes": True}


class TelegramConfigRequest(BaseModel):
    user_pin: str
    bot_token: str
    chat_id: str
    enabled: bool = True
