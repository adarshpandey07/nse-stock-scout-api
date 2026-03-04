"""Portfolio analysis, PnL, brokerage, cashflow services."""
from supabase import Client


def stock_deep_dive(db: Client, symbol: str) -> dict:
    symbol = symbol.upper()

    fund = db.table("stock_fundamentals").select("*").eq("symbol", symbol).limit(1).execute()
    fund = fund.data[0] if fund.data else None

    fundamentals = {}
    technicals = {}
    f_status = {}
    if fund:
        fundamentals = {
            "pe": fund.get("pe"), "pb": fund.get("pb"), "roe": fund.get("roe"),
            "roce": fund.get("roce"), "debt_equity": fund.get("debt_equity"),
            "market_cap": fund.get("market_cap"), "dividend_yield": fund.get("dividend_yield"),
            "promoter_holding": fund.get("promoter_holding"),
            "current_price": fund.get("current_price", 0),
        }
        technicals = {
            "rsi": fund.get("rsi", 0), "dma_50": fund.get("dma_50", 0),
            "dma_200": fund.get("dma_200", 0),
            "price_above_dma200": fund.get("price_above_dma200"),
            "dma50_above_dma200": fund.get("dma50_above_dma200"),
        }
        f_status = {
            "f1": fund.get("f1_status"), "f2": fund.get("f2_status"), "f3": fund.get("f3_status"),
            "f1_score": fund.get("f1_score", 0), "f2_score": fund.get("f2_score", 0),
            "f3_score": fund.get("f3_score", 0), "overall": fund.get("overall_score", 0),
        }

    news = db.table("news_pointer_scores").select("pointer_score").eq("symbol", symbol).limit(1).execute()
    news_score = float(news.data[0]["pointer_score"]) if news.data else 0

    holders = db.table("superstar_holdings").select("investor_id,qty,change_type").eq("symbol", symbol).execute().data
    superstar_holders = [{"investor_id": h["investor_id"], "qty": h["qty"], "change_type": h["change_type"]} for h in holders]

    scans = db.table("scan_results").select("scan_date,scanner_type,score").eq("symbol", symbol).order("scan_date", desc=True).limit(5).execute().data
    scan_results = [{"date": s["scan_date"], "scanner": s["scanner_type"], "score": s["score"]} for s in scans]

    return {
        "symbol": symbol, "fundamentals": fundamentals, "technicals": technicals,
        "news_score": news_score, "superstar_holders": superstar_holders,
        "f_status": f_status, "scan_results": scan_results,
    }


def portfolio_breakdown(db: Client, user_pin: str) -> dict:
    holdings = db.table("portfolio_snapshots").select("*").eq("user_pin", user_pin).execute().data

    sector_map = {}
    total_invested = 0.0
    total_current = 0.0
    items = []

    for h in holdings:
        invested = float(h.get("invested_value") or 0)
        current = float(h.get("current_value") or 0)
        total_invested += invested
        total_current += current

        stock = db.table("nse_instruments").select("sector").eq("symbol", h["symbol"]).limit(1).execute()
        sector = stock.data[0].get("sector", "Unknown") if stock.data else "Unknown"

        sector_map[sector] = sector_map.get(sector, 0) + current
        items.append({
            "symbol": h["symbol"], "qty": h.get("qty"), "avg_price": h.get("avg_price"),
            "current_price": h.get("current_price"), "invested": invested, "current": current,
            "pnl": float(h.get("pnl") or 0), "pnl_pct": float(h.get("pnl_pct") or 0), "sector": sector,
        })

    return {
        "holdings": items, "sector_allocation": sector_map,
        "total_invested": round(total_invested, 2), "total_current": round(total_current, 2),
        "total_pnl": round(total_current - total_invested, 2),
    }


def pnl_report(db: Client, user_pin: str, period: str = "daily") -> dict:
    trades = db.table("trades").select("*").eq("user_pin", user_pin).eq("status", "executed").order("executed_at").execute().data

    if not trades:
        return {"period": period, "total_pnl": 0, "total_trades": 0, "winning_trades": 0,
                "losing_trades": 0, "win_rate": 0, "avg_gain": 0, "avg_loss": 0,
                "best_trade": {}, "worst_trade": {}}

    gains, losses = [], []
    buy_map = {}
    for t in trades:
        if t["side"] == "buy":
            buy_map.setdefault(t["symbol"], []).append(t)
        elif t["side"] == "sell" and t["symbol"] in buy_map and buy_map[t["symbol"]]:
            buy_trade = buy_map[t["symbol"]].pop(0)
            pnl = (float(t["price"]) - float(buy_trade["price"])) * min(t["qty"], buy_trade["qty"])
            if pnl > 0:
                gains.append({"symbol": t["symbol"], "pnl": pnl})
            else:
                losses.append({"symbol": t["symbol"], "pnl": pnl})

    total_trades = len(gains) + len(losses)
    total_pnl = sum(g["pnl"] for g in gains) + sum(l["pnl"] for l in losses)
    win_rate = (len(gains) / total_trades * 100) if total_trades > 0 else 0
    avg_gain = (sum(g["pnl"] for g in gains) / len(gains)) if gains else 0
    avg_loss = (sum(l["pnl"] for l in losses) / len(losses)) if losses else 0

    return {
        "period": period, "total_pnl": round(total_pnl, 2), "total_trades": total_trades,
        "winning_trades": len(gains), "losing_trades": len(losses),
        "win_rate": round(win_rate, 2), "avg_gain": round(avg_gain, 2), "avg_loss": round(avg_loss, 2),
        "best_trade": max(gains, key=lambda x: x["pnl"]) if gains else {},
        "worst_trade": min(losses, key=lambda x: x["pnl"]) if losses else {},
    }


def brokerage_report(db: Client, user_pin: str) -> dict:
    trades = db.table("trades").select("*").eq("user_pin", user_pin).execute().data

    total_brokerage = sum(float(t.get("brokerage") or 0) for t in trades)
    total_stt = sum(float(t.get("stt") or 0) for t in trades)

    breakdown = [{
        "symbol": t["symbol"], "side": t["side"], "qty": t["qty"],
        "price": float(t["price"]), "brokerage": float(t.get("brokerage") or 0),
        "stt": float(t.get("stt") or 0),
        "total_charges": float(t.get("brokerage") or 0) + float(t.get("stt") or 0),
        "date": t.get("executed_at"),
    } for t in trades]

    return {
        "total_brokerage": round(total_brokerage, 2),
        "total_stt": round(total_stt, 2),
        "total_charges": round(total_brokerage + total_stt, 2),
        "breakdown": breakdown[-50:],
    }


def cashflow_report(db: Client, user_pin: str) -> dict:
    wallet = db.table("wallet_transactions").select("*").eq("user_pin", user_pin).limit(1).execute()
    w = wallet.data[0] if wallet.data else {}
    total_deposited = float(w.get("total_deposited", 0))
    total_withdrawn = float(w.get("total_withdrawn", 0))

    pnl = pnl_report(db, user_pin)
    net_pnl = pnl["total_pnl"]

    txns = db.table("wallet_transactions").select("*").eq("user_pin", user_pin).order("created_at").execute().data

    monthly = {}
    for t in txns:
        key = t["created_at"][:7]  # YYYY-MM
        if key not in monthly:
            monthly[key] = {"deposits": 0, "withdrawals": 0}
        if t["txn_type"] == "deposit":
            monthly[key]["deposits"] += float(t["amount"])
        elif t["txn_type"] == "withdraw":
            monthly[key]["withdrawals"] += float(t["amount"])

    return {
        "total_deposited": total_deposited, "total_withdrawn": total_withdrawn,
        "net_pnl": net_pnl, "net_cashflow": total_deposited - total_withdrawn + net_pnl,
        "monthly": [{"month": k, **v} for k, v in monthly.items()],
    }
