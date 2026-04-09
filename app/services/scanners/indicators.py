"""Shared technical indicator calculations and data helpers for scanners."""

from __future__ import annotations

import logging
from datetime import date

from supabase import Client

logger = logging.getLogger(__name__)


# ── Indicator functions (all expect newest-first arrays) ──────────────


def ema(values: list[float], period: int) -> float | None:
    """Exponential Moving Average. values[0] is most recent."""
    if len(values) < period:
        return None
    chrono = list(reversed(values))
    k = 2 / (period + 1)
    ema_val = sum(chrono[:period]) / period  # seed with SMA
    for price in chrono[period:]:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val


def sma(values: list[float], period: int) -> float | None:
    """Simple Moving Average over the most recent `period` values."""
    if len(values) < period:
        return None
    return sum(values[:period]) / period


def atr(highs: list[float], lows: list[float], closes: list[float],
        period: int = 14) -> float | None:
    """Average True Range. All arrays newest-first."""
    if len(highs) < period + 1 or len(closes) < period + 1:
        return None
    trs = []
    for i in range(period):
        pc = closes[i + 1]
        tr = max(highs[i] - lows[i], abs(highs[i] - pc), abs(lows[i] - pc))
        trs.append(tr)
    return sum(trs) / period


# ── Bulk data fetch helpers ───────────────────────────────────────────


def fetch_all_bars(db: Client, scan_date: date) -> dict[str, list[dict]]:
    """Fetch all daily_bars up to scan_date, grouped by symbol (newest first).

    Uses a single exec_sql RPC call with json_agg to fetch everything server-side,
    instead of 60+ paginated PostgREST calls.
    Uses short keys (o/h/l/c/v) to minimize payload (~4MB vs ~7.6MB).
    """
    import json as _json

    query = (
        f"SELECT symbol, "
        f"json_agg("
        f"  json_build_object('o',open,'h',high,'l',low,'c',close,'v',volume)"
        f"  ORDER BY date DESC"
        f") AS bars "
        f"FROM daily_bars "
        f"WHERE date <= '{scan_date}' "
        f"GROUP BY symbol"
    )
    result = db.rpc("exec_sql", {"query": query}).execute()
    rows = result.data or []

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        sym = row["symbol"]
        bars = row["bars"]
        if isinstance(bars, str):
            bars = _json.loads(bars)
        grouped[sym] = bars

    logger.info("Fetched bars for %d symbols via single exec_sql call", len(grouped))
    return grouped


def fetch_name_map(db: Client) -> dict[str, str]:
    """Fetch symbol → company name mapping via single exec_sql call."""
    result = db.rpc("exec_sql", {
        "query": "SELECT symbol, name FROM nse_stocks"
    }).execute()
    return {r["symbol"]: r["name"] for r in (result.data or [])}


def fetch_etf_symbols(db: Client) -> set[str]:
    """Fetch set of ETF/fund symbols to exclude from scanners."""
    result = db.rpc("exec_sql", {
        "query": (
            "SELECT symbol FROM nse_stocks "
            "WHERE name LIKE '%AMC -%' OR name LIKE '% ETF%' "
            "OR symbol LIKE '%ETF%' OR symbol LIKE '%BEES%'"
        )
    }).execute()
    return {r["symbol"] for r in (result.data or [])}
