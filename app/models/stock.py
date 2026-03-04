from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NseStock(Base):
    __tablename__ = "nse_stocks"

    symbol: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, default="")
    sector: Mapped[str] = mapped_column(String, default="")
    industry: Mapped[str] = mapped_column(String, default="")
    market_cap: Mapped[Decimal] = mapped_column(Numeric, default=0)
    isin: Mapped[str] = mapped_column(String, default="")
    series: Mapped[str] = mapped_column(String, default="EQ")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class StockFundamentals(Base):
    __tablename__ = "stock_fundamentals"

    symbol: Mapped[str] = mapped_column(String, primary_key=True)
    pe: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    pb: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    roe: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    roce: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    debt_equity: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    market_cap: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    dividend_yield: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    eps: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    book_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    face_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    promoter_holding: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    current_price: Mapped[Decimal] = mapped_column(Numeric, default=0)
    sales_growth_5y: Mapped[Decimal] = mapped_column(Numeric, default=0)
    profit_growth_5y: Mapped[Decimal] = mapped_column(Numeric, default=0)
    eps_growth_yoy: Mapped[Decimal] = mapped_column(Numeric, default=0)
    eps_growth_3y: Mapped[Decimal] = mapped_column(Numeric, default=0)
    eps_qoq_growth: Mapped[Decimal] = mapped_column(Numeric, default=0)
    sales_qoq_growth: Mapped[Decimal] = mapped_column(Numeric, default=0)
    fii_holding: Mapped[Decimal] = mapped_column(Numeric, default=0)
    fii_holding_change: Mapped[Decimal] = mapped_column(Numeric, default=0)
    volume_1m_avg: Mapped[Decimal] = mapped_column(Numeric, default=0)
    rsi: Mapped[Decimal] = mapped_column(Numeric, default=0)
    dma_50: Mapped[Decimal] = mapped_column(Numeric, default=0)
    dma_200: Mapped[Decimal] = mapped_column(Numeric, default=0)
    price_above_dma200: Mapped[bool] = mapped_column(Boolean, default=False)
    dma50_above_dma200: Mapped[bool] = mapped_column(Boolean, default=False)
    f1_status: Mapped[bool] = mapped_column(Boolean, default=False)
    f2_status: Mapped[bool] = mapped_column(Boolean, default=False)
    f3_status: Mapped[bool] = mapped_column(Boolean, default=False)
    f1_score: Mapped[Decimal] = mapped_column(Numeric, default=0)
    f2_score: Mapped[Decimal] = mapped_column(Numeric, default=0)
    f3_score: Mapped[Decimal] = mapped_column(Numeric, default=0)
    overall_score: Mapped[Decimal] = mapped_column(Numeric, default=0)
    last_calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
