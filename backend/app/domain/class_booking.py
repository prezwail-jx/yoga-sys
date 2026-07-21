import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base


CLASS_BOOKING_STATUSES = ("reserved", "checked_in", "cancelled", "absent")


class ClassBooking(Base):
    __tablename__ = "class_booking"
    __table_args__ = (
        CheckConstraint(
            "(status = 'reserved' AND terminal_by_id IS NULL AND terminal_by_role IS NULL AND terminal_at IS NULL) "
            "OR (status <> 'reserved' AND terminal_by_id IS NOT NULL AND terminal_by_role IS NOT NULL AND terminal_at IS NOT NULL)",
            name="ck_class_booking_terminal_shape",
        ),
        CheckConstraint("status = 'cancelled' OR cancellation_reason IS NULL", name="ck_class_booking_cancellation_reason"),
        Index("ix_class_booking_session_status", "class_session_id", "status"),
        Index("ix_class_booking_member_status", "member_id", "status"),
        Index("ix_class_booking_member_created", "member_id", text("created_at DESC")),
        Index(
            "uq_class_booking_active_member_session", "class_session_id", "member_id",
            unique=True, postgresql_where=text("status = 'reserved'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("class_session.id", ondelete="RESTRICT"), nullable=False
    )
    member_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("member.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(*CLASS_BOOKING_STATUSES, name="class_booking_status", create_type=False),
        default="reserved", server_default="reserved", nullable=False,
    )
    booked_by_id: Mapped[str] = mapped_column(String(64), nullable=False)
    booked_by_role: Mapped[str] = mapped_column(String(32), nullable=False)
    booked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    terminal_by_id: Mapped[str | None] = mapped_column(String(64))
    terminal_by_role: Mapped[str | None] = mapped_column(String(32))
    terminal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_reason: Mapped[str | None] = mapped_column(String(255))
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
