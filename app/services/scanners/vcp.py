"""
VCP Daily Scanner (Scanner ID = 1)

Volatility Contraction Pattern: looks for stocks where:
1. Price is above rising 50-SMA (trend)
2. ATR is contracting over recent bars
3. Recent daily ranges are tightening
4. Volume is drying up
"""

import logging
from datetime import date

from supabase import Client

from app.services.activity import log_activity
from app.services.config_service import get_active_config

logger = logging.getLogger(__name__)

SCANNER_ID = 1


def run_vcp_scanner(db: Client, scan_date: date) -> int:
    config = get_active_config(db).get("config_data", {})
    scanner_cfg = config.get("scanner_1", {})
    if not scanner_cfg.get("enabled", True):
        return 0

    weights = scanner_cfg.get("weights", {})
    w_sma = weights.get("sma_trend", 25)
    w_atr = weights.get("atr_contraction", 25)
    w_tight = weights.get("tightness", 25)
    w_vol = weights.get("volume_dry", 25)
    min_score = scanner_cfg.get("min_score", 60)
    total_weight = w_sma + w_atr + w_tight + w_vol

    fetch_cfg = config.get("fetch", {})
    min_close = fetch_cfg.get("min_close_price", 20)
    min_vol = fetch_cfg.get("min_avg_volume", 50000)

    # Get symbols with 50+ bars
    sym_result = db.rpc("exec_sql", {
        "query": f"SELECT symbol FROM daily_bars WHERE date <= '{scan_date}' GROUP BY symbol HAVING COUNT(*) >= 50"
    }).execute()
    symbols = [r["symbol"] for r in (sym_result.data or [])]

    # Delete existing results for this date + scanner
    db.table("scan_results").delete().eq("scan_date", str(scan_date)).eq("scanner_type", SCANNER_ID).execute()

    results = []
    for symbol in symbols:
        bars_result = db.rpc("exec_sql", {
            "query": f"SELECT date, open, high, low, close, volume FROM daily_bars WHERE symbol = '{symbol}' AND date <= '{scan_date}' ORDER BY date DESC LIMIT 60"
        }).execute()
        bars = bars_result.data or []

        if len(bars) < 50:
            continue

        closes = [float(b["close"]) for b in bars]
        highs = [float(b["high"]) for b in bars]
        lows = [float(b["low"]) for b in bars]
        volumes = [int(b["volume"]) for b in bars]

        current_close = closes[0]
        avg_vol_20 = sum(volumes[:20]) / 20

        if current_close < min_close or avg_vol_20 < min_vol:
            continue

        # 1. SMA Trend
        sma_50 = sum(closes[:50]) / 50
        sma_50_prev = sum(closes[1:51]) / 50 if len(closes) > 50 else sma_50
        sma_score = 0
        if current_close > sma_50:
            sma_score = 50
            if sma_50 > sma_50_prev:
                sma_score = 100

        # 2. ATR Contraction
        def calc_atr(h, l, c, period):
            trs = []
            for i in range(period):
                tr = max(h[i] - l[i], abs(h[i] - c[i + 1]) if i + 1 < len(c) else h[i] - l[i], abs(l[i] - c[i + 1]) if i + 1 < len(c) else h[i] - l[i])
                trs.append(tr)
            return sum(trs) / len(trs) if trs else 0

        atr_recent = calc_atr(highs[:10], lows[:10], closes, 10)
        atr_prior = calc_atr(highs[10:20], lows[10:20], closes[10:], 10)
        atr_score = 0
        if atr_prior > 0:
            cr = atr_recent / atr_prior
            if cr < 0.5: atr_score = 100
            elif cr < 0.7: atr_score = 75
            elif cr < 0.9: atr_score = 50
            elif cr < 1.0: atr_score = 25

        # 3. Tightness
        high_10 = max(highs[:10])
        low_10 = min(lows[:10])
        range_pct = ((high_10 - low_10) / current_close) * 100 if current_close > 0 else 999
        tight_score = 0
        if range_pct < 5: tight_score = 100
        elif range_pct < 8: tight_score = 75
        elif range_pct < 12: tight_score = 50
        elif range_pct < 15: tight_score = 25

        # 4. Volume Drying
        vol_recent = sum(volumes[:10]) / 10
        vol_prior = sum(volumes[10:30]) / 20 if len(volumes) >= 30 else sum(volumes[10:]) / max(len(volumes) - 10, 1)
        vol_score = 0
        if vol_prior > 0:
            vr = vol_recent / vol_prior
            if vr < 0.4: vol_score = 100
            elif vr < 0.6: vol_score = 75
            elif vr < 0.8: vol_score = 50
            elif vr < 1.0: vol_score = 25

        raw_score = sma_score * w_sma + atr_score * w_atr + tight_score * w_tight + vol_score * w_vol
        final_score = round(raw_score / total_weight, 2) if total_weight > 0 else 0

        if final_score >= min_score:
            results.append({
                "scan_date": str(scan_date), "symbol": symbol,
                "scanner_type": SCANNER_ID, "score": final_score,
                "metrics_json": {
                    "sma_trend": sma_score, "atr_contraction": atr_score,
                    "tightness": tight_score, "volume_dry": vol_score,
                    "range_pct_10d": round(range_pct, 2),
                    "atr_ratio": round(atr_recent / atr_prior, 3) if atr_prior > 0 else None,
                    "vol_ratio": round(vol_recent / vol_prior, 3) if vol_prior > 0 else None,
                    "close": current_close, "sma_50": round(sma_50, 2),
                },
            })

    if results:
        # Insert in batches
        for i in range(0, len(results), 100):
            db.table("scan_results").insert(results[i:i+100]).execute()

    log_activity(db, event_type="scan_completed", entity_type="scanner",
                 entity_id=str(SCANNER_ID),
                 message=f"VCP scanner completed for {scan_date}: {len(results)} stocks passed",
                 status="completed", metadata_json={"count": len(results), "total_symbols": len(symbols)})
    return len(results)
