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
    """Wilder's smoothed Average True Range. All arrays newest-first."""
    n = min(len(highs), len(lows), len(closes))
    if n < period + 1:
        return None

    # Work oldest-to-newest for sequential smoothing
    h = list(reversed(highs[:n]))
    l = list(reversed(lows[:n]))
    c = list(reversed(closes[:n]))

    # Compute True Range for each bar (from bar 1 onward)
    trs: list[float] = []
    for i in range(1, len(h)):
        prev_close = c[i - 1]
        tr = max(h[i] - l[i], abs(h[i] - prev_close), abs(l[i] - prev_close))
        trs.append(tr)

    if len(trs) < period:
        return None

    # Seed with SMA of first `period` True Ranges
    atr_val = sum(trs[:period]) / period

    # Wilder's smoothing for remaining TRs
    for tr in trs[period:]:
        atr_val = (atr_val * (period - 1) + tr) / period

    return atr_val


# ── Bulk data fetch helpers ───────────────────────────────────────────


def fetch_all_bars(db: Client, scan_date: date) -> dict[str, list[dict]]:
    """Fetch all daily_bars up to scan_date, grouped by symbol (newest first).

    Fetches in batches to avoid statement timeout on large datasets.
    Uses short keys (o/h/l/c/v) to minimize payload.
    """
    import json as _json

    # First get all distinct symbols
    sym_result = db.rpc("exec_sql", {
        "query": f"SELECT DISTINCT symbol FROM daily_bars WHERE date <= '{scan_date}' ORDER BY symbol"
    }).execute()
    all_symbols = [r["symbol"] for r in (sym_result.data or [])]

    grouped: dict[str, list[dict]] = {}
    batch_size = 300

    for i in range(0, len(all_symbols), batch_size):
        batch = all_symbols[i:i + batch_size]
        symbols_csv = ",".join(f"'{s}'" for s in batch)
        query = (
            f"SELECT symbol, "
            f"json_agg("
            f"  json_build_object('o',open,'h',high,'l',low,'c',close,'v',volume)"
            f"  ORDER BY date DESC"
            f") AS bars "
            f"FROM daily_bars "
            f"WHERE date <= '{scan_date}' AND symbol IN ({symbols_csv}) "
            f"GROUP BY symbol"
        )
        result = db.rpc("exec_sql", {"query": query}).execute()
        for row in (result.data or []):
            sym = row["symbol"]
            bars = row["bars"]
            if isinstance(bars, str):
                bars = _json.loads(bars)
            grouped[sym] = bars

    logger.info("Fetched bars for %d symbols in %d batches", len(grouped), (len(all_symbols) + batch_size - 1) // batch_size)
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
            "WHERE name LIKE '%AMC -%' OR name LIKE '%UTIAMC%' "
            "OR name LIKE '% ETF%' OR name LIKE '%Fund%' "
            "OR symbol LIKE '%ETF%' OR symbol LIKE '%BEES%' "
            "OR symbol LIKE '%GOLDBEES%' OR symbol LIKE '%GOLDBETA%'"
        )
    }).execute()
    return {r["symbol"] for r in (result.data or [])}


def _cache_listing_dates(db: Client, data: dict[str, date]) -> None:
    """Upsert listing dates into nse_stocks.listing_date for offline fallback."""
    if not data:
        return
    try:
        rows = [{"symbol": sym, "listing_date": dt.isoformat()} for sym, dt in data.items()]
        for i in range(0, len(rows), 500):
            db.table("nse_stocks").upsert(
                rows[i:i + 500], on_conflict="symbol"
            ).execute()
        logger.info("Cached listing dates for %d symbols in nse_stocks", len(data))
    except Exception as e:
        logger.warning("Failed to cache listing dates: %s", e)


def _load_cached_listing_dates(db: Client) -> dict[str, date]:
    """Load listing dates from nse_stocks cache (fallback when NSE is down)."""
    try:
        result = db.rpc("exec_sql", {
            "query": (
                "SELECT symbol, listing_date FROM nse_stocks "
                "WHERE listing_date IS NOT NULL"
            )
        }).execute()
        from datetime import datetime as _dt
        out: dict[str, date] = {}
        for r in (result.data or []):
            try:
                out[r["symbol"]] = _dt.strptime(r["listing_date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass
        logger.info("Loaded %d cached listing dates from DB", len(out))
        return out
    except Exception as e:
        logger.warning("Failed to load cached listing dates: %s", e)
        return {}


def fetch_listing_date_map(db: Client | None = None) -> dict[str, date]:
    """Fetch symbol → listing_date from NSE's EQUITY_L.csv.

    Robust strategy:
    1. Try NSE live CSV (source of truth)
    2. If success → cache to nse_stocks.listing_date for future use
    3. If NSE fails → load from DB cache
    4. If both fail → return {} (scanner falls back to bar count)
    """
    import csv
    import io
    from datetime import datetime

    import httpx

    nse_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Referer": "https://www.nseindia.com/",
    }

    try:
        with httpx.Client(headers=nse_headers, follow_redirects=True, timeout=15) as client:
            client.get("https://www.nseindia.com/")
            resp = client.get(
                "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
            )
            resp.raise_for_status()

        result: dict[str, date] = {}
        for row in csv.DictReader(io.StringIO(resp.text)):
            sym = row.get("SYMBOL", "").strip()
            raw = row.get(" DATE OF LISTING", row.get("DATE OF LISTING", "")).strip()
            if sym and raw:
                try:
                    result[sym] = datetime.strptime(raw, "%d-%b-%Y").date()
                except ValueError:
                    pass
        logger.info("Fetched listing dates for %d symbols from NSE", len(result))

        # Cache for offline fallback
        if db and result:
            _cache_listing_dates(db, result)

        return result
    except Exception as e:
        logger.warning("NSE listing date fetch failed: %s — trying DB cache", e)
        if db:
            return _load_cached_listing_dates(db)
        return {}
