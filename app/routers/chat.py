from fastapi import APIRouter, Query

from app.dependencies import CurrentUser, DB
from app.schemas.chat import ChatMessageOut, ChatMessageRequest, ChatSessionOut
from app.services.chat_service import chat, get_session_messages, get_sessions

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message")
def send_message(req: ChatMessageRequest, db: DB, _user: CurrentUser):
    result = chat(db, req.user_pin, req.message, req.session_id)
    return result


@router.get("/sessions", response_model=list[ChatSessionOut])
def list_sessions(db: DB, _user: CurrentUser, user_pin: str = Query(...)):
    return get_sessions(db, user_pin)


@router.get("/sessions/{session_id}", response_model=list[ChatMessageOut])
def get_conversation(session_id: str, db: DB, _user: CurrentUser):
    return get_session_messages(db, session_id)
