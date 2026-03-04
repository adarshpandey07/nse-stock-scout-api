"""Backtesting engine — replays scanners on historical data."""
import logging
from datetime import date

from supabase import Client

from app.services.activity import log_activity

logger = logging.getLogger(__name__)


def run_backtest(db: Client, user_pin: str, date_from: date, date_to: date,
                 strategy: str = "vcp", config: dict = None) -> dict:
    config = config or {}
    stop_loss_pct = config.get("stop_loss_pct", 5.0)
    target_pct = config.get("target_pct", 10.0)
    hold_days = config.get("hold_days", 20)
    min_score = config.get("min_score", 60)

    scanner_type = 1 if strategy == "vcp" else 2

    # Use RPC for complex query
    scan_results = db.rpc("exec_sql", {
        "query": f"""
            SELECT scan_date, symbol, score, metrics_json
            FROM scan_results
            WHERE scanner_type = {scanner_type}
              AND scan_date BETWEEN '{date_from}' AND '{date_to}'
              AND score >= {min_score}
            ORDER BY scan_date, score DESC
        """
    }).execute()

    rows = scan_results.data or []
    trades = []
    winning = 0
    total_pnl = 0.0

    for row in rows:
        scan_date = row["scan_date"]
        symbol = row["symbol"]
        entry_score = float(row["score"])

        future = db.rpc("exec_sql", {
            "query": f"""
                SELECT date, open, high, low, close
                FROM daily_bars
                WHERE symbol = '{symbol}' AND date > '{scan_date}'
                ORDER BY date
                LIMIT {hold_days + 1}
            """
        }).execute()

        future_bars = future.data or []
        if not future_bars:
            continue

        entry_price = float(future_bars[0]["open"])
        if entry_price <= 0:
            continue

        stop_loss = entry_price * (1 - stop_loss_pct / 100)
        target = entry_price * (1 + target_pct / 100)

        exit_price = entry_price
        exit_date = future_bars[0]["date"]
        exit_reason = "hold_expired"

        for bar in future_bars[1:]:
            bar_high = float(bar["high"])
            bar_low = float(bar["low"])
            bar_close = float(bar["close"])

            if bar_low <= stop_loss:
                exit_price = stop_loss
                exit_date = bar["date"]
                exit_reason = "stop_loss"
                break
            elif bar_high >= target:
                exit_price = target
                exit_date = bar["date"]
                exit_reason = "target_hit"
                break
            else:
                exit_price = bar_close
                exit_date = bar["date"]

        pnl = exit_price - entry_price
        pnl_pct = (pnl / entry_price) * 100
        total_pnl += pnl
        if pnl > 0:
            winning += 1

        trades.append({
            "symbol": symbol, "entry_date": str(scan_date),
            "entry_price": round(entry_price, 2), "exit_date": str(exit_date),
            "exit_price": round(exit_price, 2), "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2), "exit_reason": exit_reason, "score": entry_score,
        })

    total_trades = len(trades)
    win_rate = (winning / total_trades * 100) if total_trades > 0 else 0

    sharpe = 0
    if trades:
        returns = [t["pnl_pct"] for t in trades]
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        sharpe = (avg_return / std_dev) if std_dev > 0 else 0

    run_row = {
        "user_pin": user_pin,
        "date_from": str(date_from),
        "date_to": str(date_to),
        "strategy": strategy,
        "criteria_used": config,
        "result_json": {"trades": trades, "sharpe_ratio": round(sharpe, 3), "win_rate": round(win_rate, 2)},
        "total_trades": total_trades,
        "winning_trades": winning,
        "pnl": round(total_pnl, 2),
        "pnl_pct": round(win_rate, 2),
        "status": "completed",
    }
    result = db.table("backtest_runs").insert(run_row).execute()
    run = result.data[0] if result.data else run_row

    log_activity(db, event_type="backtest_completed", entity_type="backtest",
                 entity_id=run.get("id", ""),
                 message=f"Backtest {strategy}: {total_trades} trades, PnL={total_pnl:.2f}, WR={win_rate:.1f}%",
                 status="completed", metadata_json={"trades": total_trades, "pnl": total_pnl})
    return run
