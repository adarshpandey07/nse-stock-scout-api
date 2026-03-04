"""Aadarsh.AI Chat service — OpenAI GPT-4o with portal context."""
import json
import logging
import uuid
from collections.abc import Generator
from datetime import datetime, timezone

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

When presenting data, use clear formatting with bullet points and numbers.
If the user asks about a specific stock, provide analysis based on the available scan results and news.
"""


def _get_context(db: Client, user_pin: str) -> str:
    """Build rich context from the user's portfolio, watchlist, scans, news, and actions."""
    parts = []
    try:
        summary = get_dashboard_summary(db, user_pin)
        parts.append(f"""Portfolio Overview:
- Total Invested: Rs {summary['portfolio']['total_invested']:,.2f}
- Current Value: Rs {summary['portfolio']['total_current']:,.2f}
- P&L: Rs {summary['portfolio']['total_pnl']:,.2f} ({summary['portfolio']['total_pnl_pct']:.2f}%)
- Holdings: {summary['portfolio']['holdings_count']} stocks
- Wallet Balance: Rs {summary['wallet_balance']:,.2f}
- Pending Actions: {summary['pending_actions']}
- Watchlist Items: {summary['watchlist_count']}
- F-Scanner (all pass): {summary['f_scanner_summary'].get('all_pass', 0)} stocks""")

        # Add news context
        if summary.get("news_ticker"):
            news_lines = []
            for n in summary["news_ticker"]:
                sentiment = n.get("sentiment", "neutral")
                news_lines.append(f"  - [{sentiment.upper()}] {n.get('symbol', 'Market')}: {n['headline']}")
            parts.append("Recent News:\n" + "\n".join(news_lines))
    except Exception as e:
        logger.warning(f"Error building dashboard context: {e}")
        parts.append("No portfolio data available.")

    # Top scan results
    try:
        scan_res = db.table("scan_results").select("symbol,score,scanner_type").order("score", desc=True).limit(10).execute()
        if scan_res.data:
            scan_lines = [f"  - {s['symbol']} (score: {s['score']}, type: {s.get('scanner_type', 'N/A')})" for s in scan_res.data]
            parts.append("Top Scanner Picks:\n" + "\n".join(scan_lines))
    except Exception:
        pass

    # Pending actions detail
    try:
        actions_res = db.table("action_centre").select("message,action_type,symbol").eq("status", "pending").limit(5).execute()
        if actions_res.data:
            action_lines = [f"  - [{a.get('action_type', 'info')}] {a.get('symbol', '')}: {a['message']}" for a in actions_res.data]
            parts.append("Pending Actions:\n" + "\n".join(action_lines))
    except Exception:
        pass

    return "\n\n".join(parts)


def _get_or_create_session(db: Client, user_pin: str, message: str, session_id: str | None) -> str:
    """Return session ID, creating a new session if needed."""
    if session_id:
        sess = db.table("chat_sessions").select("id").eq("id", session_id).limit(1).execute()
        if sess.data:
            return sess.data[0]["id"]
    result = db.table("chat_sessions").insert({
        "user_pin": user_pin, "title": message[:50],
    }).execute()
    return result.data[0]["id"]


def _build_messages(db: Client, user_pin: str, sid: str) -> list[dict]:
    """Build the OpenAI messages array with system prompt + context + history."""
    history = db.table("chat_messages").select("role,content").eq("session_id", sid).order("created_at").execute().data
    context = _get_context(db, user_pin)
    messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context}]
    for msg in history[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    return messages


def chat_stream(db: Client, user_pin: str, message: str, session_id: str | None = None) -> Generator[str, None, None]:
    """Stream chat response as SSE events. Yields 'data: ...\n\n' strings."""
    if not settings.openai_api_key:
        error_payload = json.dumps({"error": "OpenAI API key not configured"})
        yield f"data: {error_payload}\n\n"
        yield "data: [DONE]\n\n"
        return

    sid = _get_or_create_session(db, user_pin, message, session_id)

    # Save user message
    db.table("chat_messages").insert({
        "session_id": sid, "role": "user", "content": message,
    }).execute()

    # Send session_id as first event so frontend can track it
    yield f"data: {json.dumps({'session_id': str(sid)})}\n\n"

    openai_messages = _build_messages(db, user_pin, sid)

    assistant_content = ""
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=openai_messages,
            max_tokens=1000,
            temperature=0.7,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                assistant_content += delta.content
                # Forward the raw OpenAI SSE chunk so frontend parser works unchanged
                chunk_data = {
                    "choices": [{"delta": {"content": delta.content}}]
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        error_content = f"Sorry, I encountered an error: {str(e)}"
        assistant_content = error_content
        yield f"data: {json.dumps({'choices': [{'delta': {'content': error_content}}]})}\n\n"

    yield "data: [DONE]\n\n"

    # Save assistant response
    if assistant_content:
        db.table("chat_messages").insert({
            "session_id": sid, "role": "assistant", "content": assistant_content,
        }).execute()
        db.table("chat_sessions").update({
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", sid).execute()


def chat(db: Client, user_pin: str, message: str, session_id: str | None = None) -> dict:
    """Non-streaming chat endpoint (kept for backward compat)."""
    if not settings.openai_api_key:
        return {
            "session_id": session_id or str(uuid.uuid4()),
            "response": "OpenAI API key not configured. Please add OPENAI_API_KEY to .env",
        }

    sid = _get_or_create_session(db, user_pin, message, session_id)

    # Save user message
    db.table("chat_messages").insert({
        "session_id": sid, "role": "user", "content": message,
    }).execute()

    openai_messages = _build_messages(db, user_pin, sid)

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o", messages=openai_messages, max_tokens=1000, temperature=0.7,
        )
        assistant_content = response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        assistant_content = f"Sorry, I encountered an error: {str(e)}"

    db.table("chat_messages").insert({
        "session_id": sid, "role": "assistant", "content": assistant_content,
    }).execute()

    db.table("chat_sessions").update({
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", sid).execute()

    return {"session_id": str(sid), "response": assistant_content}


def get_sessions(db: Client, user_pin: str) -> list[dict]:
    return db.table("chat_sessions").select("*").eq("user_pin", user_pin).order("updated_at", desc=True).execute().data


def get_session_messages(db: Client, session_id: str) -> list[dict]:
    return db.table("chat_messages").select("*").eq("session_id", session_id).order("created_at").execute().data
