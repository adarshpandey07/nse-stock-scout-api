from decimal import Decimal
from pydantic import BaseModel


class StockDeepDive(BaseModel):
    symbol: str
    fundamentals: dict = {}
    technicals: dict = {}
    news_score: Decimal = 0
    superstar_holders: list = []
    f_status: dict = {}
    scan_results: list = []


class PortfolioBreakdown(BaseModel):
    holdings: list = []
    sector_allocation: dict = {}
    total_invested: Decimal = 0
    total_current: Decimal = 0
    total_pnl: Decimal = 0


class PnLReport(BaseModel):
    period: str
    total_pnl: Decimal = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: Decimal = 0
    avg_gain: Decimal = 0
    avg_loss: Decimal = 0
    best_trade: dict = {}
    worst_trade: dict = {}


class BrokerageReport(BaseModel):
    total_brokerage: Decimal = 0
    total_stt: Decimal = 0
    total_charges: Decimal = 0
    breakdown: list = []


class CashflowReport(BaseModel):
    total_deposited: Decimal = 0
    total_withdrawn: Decimal = 0
    net_pnl: Decimal = 0
    net_cashflow: Decimal = 0
    monthly: list = []
