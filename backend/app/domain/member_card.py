import uuid
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Integer, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base

CARD_STATUSES = ("pending_activation", "active", "frozen", "expired", "closed")

class MemberCard(Base):
    __tablename__ = "member_card"
    __table_args__ = (
        CheckConstraint("remaining_times IS NULL OR remaining_times >= 0", name="ck_member_card_remaining_nonnegative"),
        CheckConstraint("used_times >= 0", name="ck_member_card_used_nonnegative"),
        CheckConstraint("valid_days IS NULL OR valid_days >= 0", name="ck_member_card_valid_days_nonnegative"),
        CheckConstraint("total_frozen_days >= 0", name="ck_member_card_frozen_days_nonnegative"),
        CheckConstraint("frozen_until IS NULL OR frozen_from IS NOT NULL", name="ck_member_card_freeze_dates"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("member.id", ondelete="RESTRICT"), nullable=False, index=True)
    card_product_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("card_product.id", ondelete="RESTRICT"), nullable=False)
    source_member_card_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("member_card.id", ondelete="RESTRICT"), nullable=True)
    status: Mapped[str] = mapped_column(Enum(*CARD_STATUSES, name="member_card_status", create_type=False), nullable=False)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    card_type: Mapped[str] = mapped_column(String(32), nullable=False)
    terms_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    remaining_times: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_times: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opened_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    remind_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    frozen_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    frozen_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    freeze_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_frozen_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
