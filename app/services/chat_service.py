"""Aadarsh.AI Chat service — OpenAI GPT-4o with portal context."""
import logging
import uuid

from openai import OpenAI
from supabase import Client

from app.config import settings
from app.services.dashboard_service import get_dashboard_summary

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Aadarsh.AI, an intelligent stock trading assistant for NSE Stock Scout.
You help users with:
- Analyzing stocks and portfolios
- Understanding scan results (VCP, Tight Consolidation, F1/F2/F3)
- Interpreting news sentiment and superstar portfolio changes
- Making informed trading decisions
- Explaining market concepts

You have access to the user's portfolio, watchlist, scan results, and news data.
Be concise, data-driven, and always remind users that this is not financial advice.
"""


def _get_context(db: Client, user_pin: str) -> str:
    try:
        summary = get_dashboard_summary(db, user_pin)
        return f"""User Context:
- Portfolio: {summary['portfolio']['total_invested']} invested, {summary['portfolio']['total_pnl']} PnL ({summary['portfolio']['total_pnl_pct']}%)
- Holdings: {summary['portfolio']['holdings_count']} stocks
- Wallet: {summary['wallet_balance']}
- Pending Actions: {summary['pending_actions']}
- Watchlist: {summary['watchlist_count']} items
- F-Scanner: {summary['f_scanner_summary'].get('all_pass', 0)} stocks pass all criteria
"""
    except Exception:
        return "No portfolio data available."


def chat(db: Client, user_pin: str, message: str, session_id: str | None = None) -> dict:
    if not settings.openai_api_key:
        return {
            "session_id": session_id or str(uuid.uuid4()),
            "response": "OpenAI API key not configured. Please add OPENAI_API_KEY to .env",
        }

    # Get or create session
    if session_id:
        sess = db.table("chat_sessions").select("*").eq("id", session_id).limit(1).execute()
        if not sess.data:
            result = db.table("chat_sessions").insert({
                "user_pin": user_pin, "title": message[:50],
            }).execute()
            session = result.data[0]
        else:
            session = sess.data[0]
    else:
        result = db.table("chat_sessions").insert({
            "user_pin": user_pin, "title": message[:50],
        }).execute()
        session = result.data[0]

    sid = session["id"]

    # Save user message
    db.table("chat_messages").insert({
        "session_id": sid, "role": "user", "content": message,
    }).execute()

    # Build conversation history
    history = db.table("chat_messages").select("role,content").eq("session_id", sid).order("created_at").execute().data

    context = _get_context(db, user_pin)
    messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context}]
    for msg in history[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o", messages=messages, max_tokens=1000, temperature=0.7,
        )
        assistant_content = response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        assistant_content = f"Sorry, I encountered an error: {str(e)}"

    db.table("chat_messages").insert({
        "session_id": sid, "role": "assistant", "content": assistant_content,
    }).execute()

    from datetime import datetime, timezone
    db.table("chat_sessions").update({
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", sid).execute()

    return {"session_id": str(sid), "response": assistant_content}


def get_sessions(db: Client, user_pin: str) -> list[dict]:
    return db.table("chat_sessions").select("*").eq("user_pin", user_pin).order("updated_at", desc=True).execute().data


def get_session_messages(db: Client, session_id: str) -> list[dict]:
    return db.table("chat_messages").select("*").eq("session_id", session_id).order("created_at").execute().data
