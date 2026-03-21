"""Pydantic schemas for Polymarket trading module."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


# ── Config ──


class PmConfigUpdate(BaseModel):
    wallet_address: str | None = None
    paper_mode: bool | None = None
    max_position_usd: Decimal | None = None
    max_total_exposure_usd: Decimal | None = None
    kelly_fraction: Decimal | None = None
    auto_trade: bool | None = None
    strategies_enabled: list[str] | None = None


class PmConfigOut(BaseModel):
    id: str
    user_pin: str
    wallet_address: str | None = None
    proxy_wallet_address: str | None = None
    chain_id: int
    paper_mode: bool
    max_position_usd: Decimal
    max_total_exposure_usd: Decimal
    kelly_fraction: Decimal
    auto_trade: bool
    strategies_enabled: list
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Markets ──


class PmMarketOut(BaseModel):
    id: str
    condition_id: str
    question: str
    description: str
    category: str
    end_date: datetime | None = None
    tokens: list
    volume_24h: Decimal
    liquidity: Decimal
    yes_price: Decimal | None = None
    no_price: Decimal | None = None
    spread: Decimal | None = None
    active: bool
    resolution_source: str
    tags: list
    last_synced_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Signals ──


class PmSignalOut(BaseModel):
    id: str
    condition_id: str
    strategy: str
    signal_type: str
    token_id: str
    side: str
    recommended_price: Decimal
    recommended_size: Decimal
    estimated_edge: Decimal | None = None
    ai_probability: Decimal | None = None
    market_probability: Decimal | None = None
    confidence: str
    reasoning: str
    news_context: str
    status: str
    action_centre_id: str | None = None
    expires_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PmSignalDecision(BaseModel):
    decided_by: str


# ── Orders ──


class PmOrderRequest(BaseModel):
    signal_id: str | None = None
    condition_id: str | None = None
    token_id: str | None = None
    side: str | None = None
    price: Decimal | None = None
    size: Decimal | None = None
    order_type: str = "GTC"


class PmOrderOut(BaseModel):
    id: str
    user_pin: str
    signal_id: str | None = None
    condition_id: str
    token_id: str
    side: str
    price: Decimal
    size: Decimal
    order_type: str
    paper_mode: bool
    clob_order_id: str | None = None
    status: str
    filled_size: Decimal
    avg_fill_price: Decimal | None = None
    fee_paid: Decimal
    tx_hash: str | None = None
    error_message: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Positions ──


class PmPositionOut(BaseModel):
    id: str
    user_pin: str
    condition_id: str
    token_id: str
    outcome: str
    question: str
    size: Decimal
    avg_entry_price: Decimal
    current_price: Decimal
    cost_basis: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_pct: Decimal
    strategy: str
    paper_mode: bool
    status: str
    resolved_outcome: str | None = None
    realized_pnl: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── P&L Snapshots ──


class PmPnlSnapshotOut(BaseModel):
    id: str
    user_pin: str
    snapshot_date: str
    total_invested: Decimal
    total_market_value: Decimal
    total_unrealized_pnl: Decimal
    total_realized_pnl: Decimal
    open_positions: int
    strategy_breakdown: dict
    paper_mode: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Strategy Stats ──


class PmStrategyStatsOut(BaseModel):
    id: str
    user_pin: str
    strategy: str
    total_signals: int
    signals_executed: int
    winning_trades: int
    losing_trades: int
    total_invested: Decimal
    total_returned: Decimal
    net_pnl: Decimal
    win_rate: Decimal
    avg_edge_realized: Decimal
    paper_mode: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Dashboard ──


class PmDashboardOut(BaseModel):
    total_invested: Decimal = Decimal("0")
    total_market_value: Decimal = Decimal("0")
    total_unrealized_pnl: Decimal = Decimal("0")
    total_realized_pnl: Decimal = Decimal("0")
    open_positions: int = 0
    pending_signals: int = 0
    recent_signals: list = []
    recent_orders: list = []
    strategy_stats: list = []
    paper_mode: bool = True
