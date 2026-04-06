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
    """Fetch all daily_bars up to scan_date, grouped by symbol (newest first)."""
    all_rows: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        batch = (
            db.table("daily_bars")
            .select("symbol, date, open, high, low, close, volume")
            .lte("date", str(scan_date))
            .range(offset, offset + page_size - 1)
            .execute()
            .data
        )
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    grouped: dict[str, list[dict]] = {}
    for row in all_rows:
        sym = row["symbol"]
        if sym not in grouped:
            grouped[sym] = []
        grouped[sym].append(row)

    for bars in grouped.values():
        bars.sort(key=lambda x: x["date"], reverse=True)

    logger.info("Fetched %d bars for %d symbols", len(all_rows), len(grouped))
    return grouped


def fetch_name_map(db: Client) -> dict[str, str]:
    """Fetch symbol → company name mapping."""
    all_rows: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        batch = (
            db.table("nse_stocks")
            .select("symbol, name")
            .range(offset, offset + page_size - 1)
            .execute()
            .data
        )
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return {r["symbol"]: r["name"] for r in all_rows}
