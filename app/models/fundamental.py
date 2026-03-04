import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FCriteriaConfig(Base):
    __tablename__ = "f_criteria_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    criteria_group: Mapped[str] = mapped_column(String, nullable=False)  # F1, F2, F3
    condition_name: Mapped[str] = mapped_column(String, nullable=False)
    field_name: Mapped[str] = mapped_column(String, nullable=False)
    operator: Mapped[str] = mapped_column(String, nullable=False, default=">")
    value: Mapped[Decimal] = mapped_column(Numeric, default=0)
    description: Mapped[str] = mapped_column(String, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class FScanRun(Base):
    __tablename__ = "f_scan_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    criteria_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    total_stocks: Mapped[int] = mapped_column(Integer, default=0)
    f1_pass: Mapped[int] = mapped_column(Integer, default=0)
    f2_pass: Mapped[int] = mapped_column(Integer, default=0)
    f3_pass: Mapped[int] = mapped_column(Integer, default=0)
    all_pass: Mapped[int] = mapped_column(Integer, default=0)
    results: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
