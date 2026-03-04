from decimal import Decimal
from pydantic import BaseModel


class PortfolioSummary(BaseModel):
    total_invested: Decimal = 0
    total_current: Decimal = 0
    total_pnl: Decimal = 0
    total_pnl_pct: Decimal = 0
    holdings_count: int = 0


class DashboardSummary(BaseModel):
    portfolio: PortfolioSummary
    wallet_balance: Decimal = 0
    pending_actions: int = 0
    watchlist_count: int = 0
    latest_scan_results: int = 0
    news_ticker: list = []
    f_scanner_summary: dict = {}
