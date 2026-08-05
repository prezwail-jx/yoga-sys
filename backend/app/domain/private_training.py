import uuid
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base


PRIVATE_SLOT_STATUSES = ("available", "locked", "cancelled")
PRIVATE_BOOKING_STATUSES = ("pending", "confirmed", "rejected", "cancelled", "completed")
ACTIVE_PRIVATE_BOOKING_STATUSES = ("pending", "confirmed")
ACTIVE_PRIVATE_SLOT_STATUSES = ("available", "locked")


class PrivateAvailability(Base):
    __tablename__ = "private_availability"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_private_availability_time_order"),
        CheckConstraint("duration_minutes > 0", name="ck_private_availability_duration_positive"),
        Index("ix_private_availability_coach_time", "coach_profile_id", "start_at", "end_at"),
        Index("ix_private_availability_status_time", "status", "start_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coach_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("coach_profile.id", ondelete="RESTRICT"), nullable=False
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(*PRIVATE_SLOT_STATUSES, name="private_availability_status", create_type=False),
        nullable=False, default="available", server_default="available",
    )
    created_by_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PrivateBooking(Base):
    __tablename__ = "private_booking"
    __table_args__ = (
        CheckConstraint(
            "(status IN ('pending', 'confirmed') AND terminal_by_id IS NULL AND terminal_by_role IS NULL AND terminal_at IS NULL) "
            "OR (status IN ('rejected', 'cancelled', 'completed') AND terminal_by_id IS NOT NULL AND terminal_by_role IS NOT NULL AND terminal_at IS NOT NULL)",
            name="ck_private_booking_terminal_shape",
        ),
        CheckConstraint(
            "status NOT IN ('confirmed', 'completed') OR member_card_id IS NOT NULL",
            name="ck_private_booking_confirmed_card",
        ),
        CheckConstraint("status = 'rejected' OR rejection_reason IS NULL", name="ck_private_booking_rejection_reason"),
        CheckConstraint("status = 'cancelled' OR cancellation_reason IS NULL", name="ck_private_booking_cancellation_reason"),
        Index("ix_private_booking_slot_status", "availability_id", "status"),
        Index("ix_private_booking_member_status", "member_id", "status"),
        Index("ix_private_booking_coach_status", "coach_profile_id", "status"),
        Index(
            "uq_private_booking_active_slot", "availability_id", unique=True,
            postgresql_where=text("status IN ('pending', 'confirmed')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    availability_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("private_availability.id", ondelete="RESTRICT"), nullable=False
    )
    member_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("member.id", ondelete="RESTRICT"), nullable=False)
    coach_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("coach_profile.id", ondelete="RESTRICT"), nullable=False
    )
    member_card_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("member_card.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(
        Enum(*PRIVATE_BOOKING_STATUSES, name="private_booking_status", create_type=False),
        nullable=False, default="pending", server_default="pending",
    )
    member_message: Mapped[str | None] = mapped_column(String(500))
    rejection_reason: Mapped[str | None] = mapped_column(String(255))
    cancellation_reason: Mapped[str | None] = mapped_column(String(255))
    booked_by_id: Mapped[str] = mapped_column(String(64), nullable=False)
    booked_by_role: Mapped[str] = mapped_column(String(32), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    terminal_by_id: Mapped[str | None] = mapped_column(String(64))
    terminal_by_role: Mapped[str | None] = mapped_column(String(32))
    terminal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PrivateLessonRecord(Base):
    __tablename__ = "private_lesson_record"
    __table_args__ = (
        CheckConstraint("consumed_hours > 0", name="ck_private_lesson_consumed_hours_positive"),
        Index("ix_private_lesson_member_completed", "member_id", "completed_at"),
        Index("ix_private_lesson_coach_completed", "coach_profile_id", "completed_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("private_booking.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    member_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("member.id", ondelete="RESTRICT"), nullable=False)
    coach_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("coach_profile.id", ondelete="RESTRICT"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    consumed_hours: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    member_status_notes: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
