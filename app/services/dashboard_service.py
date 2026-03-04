"""Dashboard aggregation service."""
from supabase import Client


def get_dashboard_summary(db: Client, user_pin: str) -> dict:
    # Portfolio summary
    holdings = db.table("user_portfolio").select("*").eq("user_pin", user_pin).execute().data
    total_invested = sum(float(h.get("invested_value") or 0) for h in holdings)
    total_current = sum(float(h.get("current_value") or 0) for h in holdings)
    total_pnl = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    # Wallet
    wallet_res = db.table("user_wallets").select("balance").eq("user_pin", user_pin).order("created_at", desc=True).limit(1).execute()
    wallet_balance = float(wallet_res.data[0]["balance"]) if wallet_res.data else 0

    # Pending actions
    actions_res = db.table("action_centre").select("id", count="exact").eq("status", "pending").execute()
    pending_actions = actions_res.count or 0

    # Watchlist count
    wl_res = db.table("watchlist_items").select("id", count="exact").eq("user_pin", user_pin).execute()
    watchlist_count = wl_res.count or 0

    # Latest scan results
    from app.utils import last_trading_day
    scan_date = last_trading_day()
    scan_res = db.table("scan_results").select("id", count="exact").eq("scan_date", str(scan_date)).execute()
    latest_scans = scan_res.count or 0

    # News ticker (last 5)
    news_res = db.table("stock_news").select("headline,symbol,sentiment").order("published_at", desc=True).limit(5).execute()
    news_ticker = [{"headline": n["headline"], "symbol": n.get("symbol"), "sentiment": n.get("sentiment")} for n in news_res.data]

    # F-scanner summary
    f_res = (
        db.table("stock_fundamentals")
        .select("id", count="exact")
        .eq("f1_status", "pass")
        .eq("f2_status", "pass")
        .eq("f3_status", "pass")
        .execute()
    )
    f_all = f_res.count or 0

    return {
        "portfolio": {
            "total_invested": round(total_invested, 2),
            "total_current": round(total_current, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "holdings_count": len(holdings),
        },
        "wallet_balance": wallet_balance,
        "pending_actions": pending_actions,
        "watchlist_count": watchlist_count,
        "latest_scan_results": latest_scans,
        "news_ticker": news_ticker,
        "f_scanner_summary": {"all_pass": f_all},
    }
