import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_pin: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    watchlist_type: Mapped[str] = mapped_column(String, default="long_term")  # long_term, short_term
    notes: Mapped[str] = mapped_column(String, default="")
    f1_status: Mapped[bool] = mapped_column(Boolean, default=False)
    f2_status: Mapped[bool] = mapped_column(Boolean, default=False)
    f3_status: Mapped[bool] = mapped_column(Boolean, default=False)
    news_score: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[Decimal] = mapped_column(Numeric, default=0)
    sector: Mapped[str] = mapped_column(String, default="")
    close_price: Mapped[Decimal] = mapped_column(Numeric, default=0)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
