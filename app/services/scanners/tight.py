"""
Tight Consolidation Scanner (Scanner ID = 2)

Looks for stocks trading in a tight range for N days:
1. N-day price range as % of close is below threshold
2. Volume is contracting vs prior period
3. More days in range = higher score
"""

import logging
from datetime import date

from supabase import Client

from app.services.activity import log_activity
from app.services.config_service import get_active_config
from app.services.scanners.indicators import fetch_all_bars, fetch_name_map, fetch_etf_symbols

logger = logging.getLogger(__name__)

SCANNER_ID = 2


def run_tight_scanner(db: Client, scan_date: date) -> int:
    config = get_active_config(db).get("config_data", {})
    scanner_cfg = config.get("scanner_2", {})
    if not scanner_cfg.get("enabled", True):
        return 0

    weights = scanner_cfg.get("weights", {})
    w_range = weights.get("range_tightness", 40)
    w_vol = weights.get("volume_contraction", 30)
    w_days = weights.get("days_in_range", 30)
    total_weight = w_range + w_vol + w_days

    lookback = scanner_cfg.get("lookback_days", 20)
    max_range_pct = scanner_cfg.get("max_range_pct", 10.0)
    min_score = scanner_cfg.get("min_score", 50)

    fetch_cfg = config.get("fetch", {})
    min_close = fetch_cfg.get("min_close_price", 20)
    min_vol = fetch_cfg.get("min_avg_volume", 50000)

    # Bulk fetch all bars + names in 2 API calls instead of N per-symbol calls
    bars_by_symbol = fetch_all_bars(db, scan_date)
    name_map = fetch_name_map(db)
    etf_symbols = fetch_etf_symbols(db)

    results = []
    total = len(bars_by_symbol)

    for symbol, bars in bars_by_symbol.items():
        if symbol in etf_symbols:
            continue
        if len(bars) < lookback:
            continue

        closes = [float(b["c"]) for b in bars]
        highs = [float(b["h"]) for b in bars]
        lows = [float(b["l"]) for b in bars]
        volumes = [int(b["v"]) for b in bars]

        current_close = closes[0]
        avg_vol_20 = sum(volumes[:20]) / min(20, len(volumes))

        if current_close < min_close or avg_vol_20 < min_vol:
            continue

        high_n = max(highs[:lookback])
        low_n = min(lows[:lookback])
        range_pct = ((high_n - low_n) / current_close) * 100 if current_close > 0 else 999

        if range_pct > max_range_pct:
            continue

        range_score = 0
        if range_pct < 3: range_score = 100
        elif range_pct < 5: range_score = 80
        elif range_pct < 7: range_score = 60
        elif range_pct < max_range_pct: range_score = 40

        vol_lookback = sum(volumes[:lookback]) / lookback
        vol_prior = sum(volumes[lookback:lookback+20]) / 20 if len(volumes) >= lookback + 20 else sum(volumes[lookback:]) / max(len(volumes) - lookback, 1)

        vol_score = 0
        if vol_prior > 0:
            vr = vol_lookback / vol_prior
            if vr < 0.4: vol_score = 100
            elif vr < 0.6: vol_score = 75
            elif vr < 0.8: vol_score = 50
            elif vr < 1.0: vol_score = 25

        midpoint = (high_n + low_n) / 2
        tolerance = (high_n - low_n) * 0.6
        days_in = sum(1 for i in range(min(lookback, len(closes))) if abs(closes[i] - midpoint) <= tolerance)
        days_score = min(100, int((days_in / lookback) * 120))

        raw_score = range_score * w_range + vol_score * w_vol + days_score * w_days
        final_score = round(raw_score / total_weight, 2) if total_weight > 0 else 0

        if final_score >= min_score:
            vol_ratio = round(vol_lookback / vol_prior, 4) if vol_prior > 0 else 0

            results.append({
                "scan_date": str(scan_date), "symbol": symbol,
                "scanner_type": SCANNER_ID, "score": int(round(final_score)),
                "close_price": round(current_close, 2),
                "range_pct": round(range_pct, 2),
                "volume_dry_ratio": vol_ratio,
                "scanner_tag": "tight",
                "company_name": name_map.get(symbol, symbol),
            })

    # Delete old + insert new back-to-back to avoid race condition with frontend polling
    db.table("scan_results").delete().eq("scan_date", str(scan_date)).eq("scanner_type", SCANNER_ID).execute()
    for i in range(0, len(results), 100):
        db.table("scan_results").insert(results[i:i+100]).execute()

    log_activity(db, event_type="scan_completed", entity_type="scanner",
                 entity_id=str(SCANNER_ID),
                 message=f"Tight Consolidation scanner completed for {scan_date}: {len(results)} stocks passed",
                 status="completed", metadata_json={"count": len(results), "total_symbols": total})
    return len(results)
