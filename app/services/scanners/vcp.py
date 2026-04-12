"""
VCP Daily Scanner (Scanner ID = 1)

Volatility Contraction Pattern — ALL conditions must pass:
 1. Close > 20
 2. Close > EMA(Close, 50)
 3. EMA(Close, 50) > EMA(Close, 150)
 4. EMA(Close, 150) > EMA(Close, 200)  — skipped if < 200 bars
 5. Close > Max(20d High) × 0.95
 6. Max(20d High) − Min(20d Low) < Max(60d High) − Min(60d Low)
 7. Max(10d High) − Min(10d Low) < Max(20d High) − Min(20d Low)
 8. SMA(Volume, 10) < SMA(Volume, 50)
 9. Close × Volume > 1,000,000
10. ATR(14) / Close < 0.06
11. Long EMA rising vs 10 days ago  — uses EMA(200) if available, else EMA(150)
"""

import logging
from datetime import date

from supabase import Client

from app.services.activity import log_activity
from app.services.scanners.indicators import (
    atr, ema, sma, fetch_all_bars, fetch_name_map, fetch_etf_symbols,
)

logger = logging.getLogger(__name__)

SCANNER_ID = 1


def run_vcp_scanner(db: Client, scan_date: date) -> int:
    bars_by_symbol = fetch_all_bars(db, scan_date)
    name_map = fetch_name_map(db)
    etf_symbols = fetch_etf_symbols(db)

    results = []
    total = len(bars_by_symbol)

    for symbol, bars in bars_by_symbol.items():
        if symbol in etf_symbols:
            continue
        closes = [float(b["c"]) for b in bars]
        highs = [float(b["h"]) for b in bars]
        lows = [float(b["l"]) for b in bars]
        volumes = [int(b["v"]) for b in bars]

        close = closes[0]
        vol = volumes[0]

        # 1. Close > 20
        if close <= 20:
            continue

        # 2. Close > EMA(Close, 50)
        ema50 = ema(closes, 50)
        if ema50 is None or close <= ema50:
            continue

        # 3. EMA(50) > EMA(150)
        ema150 = ema(closes, 150)
        if ema150 is None or ema50 <= ema150:
            continue

        # 4. EMA(150) > EMA(200) — skip if not enough bars; 0.5% tolerance
        #    for limited-history EMA seed drift vs Chartink's longer history
        ema200 = ema(closes, 200)
        if ema200 is not None and ema150 < ema200 * 0.995:
            continue

        # 5. Close > Max(20d High) × 0.95
        if len(highs) < 20:
            continue
        max20h = max(highs[:20])
        if close <= max20h * 0.95:
            continue

        # 6. 20d range < 60d range
        if len(highs) < 60:
            continue
        r20 = max(highs[:20]) - min(lows[:20])
        r60 = max(highs[:60]) - min(lows[:60])
        if r20 >= r60:
            continue

        # 7. 10d range < 20d range
        r10 = max(highs[:10]) - min(lows[:10])
        if r10 >= r20:
            continue

        # 8. SMA(Volume, 10) < SMA(Volume, 50)
        sv10 = sma(volumes, 10)
        sv50 = sma(volumes, 50)
        if sv10 is None or sv50 is None or sv10 >= sv50:
            continue

        # 9. Turnover > ₹10 lakh
        if close * vol <= 1_000_000:
            continue

        # 10. ATR(14) / Close < 0.06
        atr14 = atr(highs, lows, closes)
        if atr14 is None or atr14 / close >= 0.06:
            continue

        # 11. Long EMA rising — use EMA(200) if available, else EMA(150)
        if ema200 is not None and len(closes) >= 210:
            ema_ago = ema(closes[10:], 200)
            if ema_ago is None or ema200 <= ema_ago:
                continue
        else:
            # Fallback for stocks with < 200 bars: use EMA(150) rising
            if len(closes) >= 160:
                ema150_ago = ema(closes[10:], 150)
                if ema150_ago is None or ema150 <= ema150_ago:
                    continue
            else:
                continue

        # ── All conditions passed ──
        range_pct = round((r10 / close) * 100, 2) if close > 0 else 0
        vol_ratio = round(sv10 / sv50, 4) if sv50 > 0 else 0

        results.append({
            "scan_date": str(scan_date),
            "symbol": symbol,
            "scanner_type": SCANNER_ID,
            "score": 100,
            "close_price": round(close, 2),
            "range_pct": range_pct,
            "volume_dry_ratio": vol_ratio,
            "scanner_tag": "vcp",
            "company_name": name_map.get(symbol, symbol),
        })

    # Delete old + insert new back-to-back to avoid race condition with frontend polling
    db.table("scan_results").delete() \
        .eq("scan_date", str(scan_date)) \
        .eq("scanner_type", SCANNER_ID).execute()
    for i in range(0, len(results), 100):
        db.table("scan_results").insert(results[i:i + 100]).execute()

    log_activity(
        db, event_type="scan_completed", entity_type="scanner",
        entity_id=str(SCANNER_ID),
        message=f"VCP scanner: {len(results)}/{total} passed all conditions on {scan_date}",
        status="completed",
        metadata_json={"count": len(results), "total_symbols": total},
    )
    return len(results)
