import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserPortfolio(Base):
    __tablename__ = "user_portfolio"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_pin: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    avg_price: Mapped[Decimal] = mapped_column(Numeric, nullable=False, default=0)
    qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_price: Mapped[Decimal] = mapped_column(Numeric, default=0)
    invested_value: Mapped[Decimal] = mapped_column(Numeric, default=0)
    current_value: Mapped[Decimal] = mapped_column(Numeric, default=0)
    pnl: Mapped[Decimal] = mapped_column(Numeric, default=0)
    pnl_pct: Mapped[Decimal] = mapped_column(Numeric, default=0)
    portfolio_type: Mapped[str] = mapped_column(String, default="long_term")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_pin: Mapped[str] = mapped_column(String, nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    holdings: Mapped[list] = mapped_column(JSONB, default=list)
    total_invested: Mapped[Decimal] = mapped_column(Numeric, default=0)
    total_current: Mapped[Decimal] = mapped_column(Numeric, default=0)
    total_pnl: Mapped[Decimal] = mapped_column(Numeric, default=0)
    total_pnl_pct: Mapped[Decimal] = mapped_column(Numeric, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
