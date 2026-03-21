"""SQLAlchemy models for Polymarket trading tables (reference only — app uses Supabase REST)."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PmConfig(Base):
    __tablename__ = "pm_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_pin: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    wallet_address: Mapped[str | None] = mapped_column(String, nullable=True)
    private_key_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    proxy_wallet_address: Mapped[str | None] = mapped_column(String, nullable=True)
    chain_id: Mapped[int] = mapped_column(Integer, default=137)
    paper_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    max_position_usd: Mapped[Decimal] = mapped_column(Numeric, default=50)
    max_total_exposure_usd: Mapped[Decimal] = mapped_column(Numeric, default=500)
    kelly_fraction: Mapped[Decimal] = mapped_column(Numeric, default=0.25)
    auto_trade: Mapped[bool] = mapped_column(Boolean, default=False)
    strategies_enabled: Mapped[dict] = mapped_column(JSONB, default=lambda: ["arb"])
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PmMarket(Base):
    __tablename__ = "pm_markets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condition_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    question: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String, default="")
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tokens: Mapped[dict] = mapped_column(JSONB, nullable=False)
    volume_24h: Mapped[Decimal] = mapped_column(Numeric, default=0)
    liquidity: Mapped[Decimal] = mapped_column(Numeric, default=0)
    yes_price: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    no_price: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    spread: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    resolution_source: Mapped[str] = mapped_column(String, default="")
    tags: Mapped[dict] = mapped_column(JSONB, default=list)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PmSignal(Base):
    __tablename__ = "pm_signals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condition_id: Mapped[str] = mapped_column(String, nullable=False)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    signal_type: Mapped[str] = mapped_column(String, nullable=False)
    token_id: Mapped[str] = mapped_column(String, nullable=False)
    side: Mapped[str] = mapped_column(String, nullable=False)
    recommended_price: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    recommended_size: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    estimated_edge: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    ai_probability: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    market_probability: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    confidence: Mapped[str] = mapped_column(String, default="medium")
    reasoning: Mapped[str] = mapped_column(Text, default="")
    news_context: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="pending")
    action_centre_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PmOrder(Base):
    __tablename__ = "pm_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_pin: Mapped[str] = mapped_column(String, nullable=False)
    signal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    condition_id: Mapped[str] = mapped_column(String, nullable=False)
    token_id: Mapped[str] = mapped_column(String, nullable=False)
    side: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    size: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    order_type: Mapped[str] = mapped_column(String, default="GTC")
    paper_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    clob_order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    filled_size: Mapped[Decimal] = mapped_column(Numeric, default=0)
    avg_fill_price: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    fee_paid: Mapped[Decimal] = mapped_column(Numeric, default=0)
    tx_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PmPosition(Base):
    __tablename__ = "pm_positions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_pin: Mapped[str] = mapped_column(String, nullable=False)
    condition_id: Mapped[str] = mapped_column(String, nullable=False)
    token_id: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    question: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[Decimal] = mapped_column(Numeric, default=0)
    avg_entry_price: Mapped[Decimal] = mapped_column(Numeric, default=0)
    current_price: Mapped[Decimal] = mapped_column(Numeric, default=0)
    cost_basis: Mapped[Decimal] = mapped_column(Numeric, default=0)
    market_value: Mapped[Decimal] = mapped_column(Numeric, default=0)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric, default=0)
    unrealized_pnl_pct: Mapped[Decimal] = mapped_column(Numeric, default=0)
    strategy: Mapped[str] = mapped_column(String, default="")
    paper_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String, default="open")
    resolved_outcome: Mapped[str | None] = mapped_column(String, nullable=True)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PmPnlSnapshot(Base):
    __tablename__ = "pm_pnl_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_pin: Mapped[str] = mapped_column(String, nullable=False)
    snapshot_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    total_invested: Mapped[Decimal] = mapped_column(Numeric, default=0)
    total_market_value: Mapped[Decimal] = mapped_column(Numeric, default=0)
    total_unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric, default=0)
    total_realized_pnl: Mapped[Decimal] = mapped_column(Numeric, default=0)
    open_positions: Mapped[int] = mapped_column(Integer, default=0)
    strategy_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)
    paper_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PmStrategyStats(Base):
    __tablename__ = "pm_strategy_stats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_pin: Mapped[str] = mapped_column(String, nullable=False)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    total_signals: Mapped[int] = mapped_column(Integer, default=0)
    signals_executed: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    total_invested: Mapped[Decimal] = mapped_column(Numeric, default=0)
    total_returned: Mapped[Decimal] = mapped_column(Numeric, default=0)
    net_pnl: Mapped[Decimal] = mapped_column(Numeric, default=0)
    win_rate: Mapped[Decimal] = mapped_column(Numeric, default=0)
    avg_edge_realized: Mapped[Decimal] = mapped_column(Numeric, default=0)
    paper_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
