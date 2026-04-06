"""
IPO Base Scanner (Scanner ID = 3)

Three groups — ALL must pass:

Group 1 (Recently listed):
  Stock FAILS SMA(Close, 400) > 0  →  stock has < 400 bars of data

Group 2 (Liquidity):
  Close > 50  AND  Volume > 100,000

Group 3 (Technical tightening — ALL):
  a) Close > Max(60d High) × 0.85
  b) Max(10d H) − Min(10d L) < (Max(40d H) − Min(40d L)) × 0.5
  c) SMA(Volume, 10) < SMA(Volume, 50)
  d) ATR(14) / Close < 0.07
"""

import logging
from datetime import date

from supabase import Client

from app.services.activity import log_activity
from app.services.scanners.indicators import (
    atr, sma, fetch_all_bars, fetch_name_map,
)

logger = logging.getLogger(__name__)

SCANNER_ID = 3


def run_ipo_scanner(db: Client, scan_date: date) -> int:
    bars_by_symbol = fetch_all_bars(db, scan_date)
    name_map = fetch_name_map(db)

    db.table("scan_results").delete() \
        .eq("scan_date", str(scan_date)) \
        .eq("scanner_type", SCANNER_ID).execute()

    results = []
    total = len(bars_by_symbol)

    for symbol, bars in bars_by_symbol.items():
        closes = [float(b["c"]) for b in bars]
        highs = [float(b["h"]) for b in bars]
        lows = [float(b["l"]) for b in bars]
        volumes = [int(b["v"]) for b in bars]

        close = closes[0]
        vol = volumes[0]

        # ── Group 1: Recently listed (< 400 trading days) ──
        if len(closes) >= 400:
            continue

        # ── Group 2: Liquidity ──
        if close <= 50:
            continue
        if vol <= 100_000:
            continue

        # ── Group 3: Technical tightening ──
        if len(bars) < 10:
            continue

        # 3a. Close > Max(60d High) × 0.85
        n60 = min(60, len(highs))
        max_h = max(highs[:n60])
        if close <= max_h * 0.85:
            continue

        # 3b. 10d range < 40d range × 0.5
        r10 = max(highs[:10]) - min(lows[:10])
        n40 = min(40, len(highs))
        r40 = max(highs[:n40]) - min(lows[:n40])
        if r40 > 0 and r10 >= r40 * 0.5:
            continue

        # 3c. SMA(Volume, 10) < SMA(Volume, 50)
        sv10 = sma(volumes, 10)
        sv50 = sma(volumes, 50)
        if sv10 is None:
            continue
        # If < 50 bars, skip volume comparison (expected for fresh IPOs)
        if sv50 is not None and sv10 >= sv50:
            continue

        # 3d. ATR(14) / Close < 0.07
        atr14 = atr(highs, lows, closes)
        if atr14 is None or atr14 / close >= 0.07:
            continue

        # ── All groups passed ──
        range_pct = round((r10 / close) * 100, 2) if close > 0 else 0
        vol_ratio = round(sv10 / sv50, 4) if sv50 and sv50 > 0 else 0

        results.append({
            "scan_date": str(scan_date),
            "symbol": symbol,
            "scanner_type": SCANNER_ID,
            "score": 100,
            "close_price": round(close, 2),
            "range_pct": range_pct,
            "volume_dry_ratio": vol_ratio,
            "scanner_tag": "ipo",
            "company_name": name_map.get(symbol, symbol),
        })

    for i in range(0, len(results), 100):
        db.table("scan_results").insert(results[i:i + 100]).execute()

    log_activity(
        db, event_type="scan_completed", entity_type="scanner",
        entity_id=str(SCANNER_ID),
        message=f"IPO scanner: {len(results)}/{total} passed all conditions on {scan_date}",
        status="completed",
        metadata_json={"count": len(results), "total_symbols": total},
    )
    return len(results)
