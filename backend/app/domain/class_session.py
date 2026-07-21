import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base


CLASS_SESSION_STATUSES = ("draft", "published", "paused", "cancelled", "completed")


class ClassSession(Base):
    __tablename__ = "class_session"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_class_session_time_order"),
        CheckConstraint("capacity > 0", name="ck_class_session_capacity_positive"),
        CheckConstraint("booking_open_hours_before >= 0", name="ck_class_session_booking_open_nonnegative"),
        CheckConstraint("booking_close_minutes_before >= 0", name="ck_class_session_booking_close_nonnegative"),
        CheckConstraint("cancel_cutoff_minutes_before >= 0", name="ck_class_session_cancel_cutoff_nonnegative"),
        Index("ix_class_session_start_status", "start_at", "status"),
        Index(
            "ix_class_session_coach_time", "coach_profile_id", "start_at", "end_at",
            postgresql_where=text("status IN ('draft', 'published', 'paused')"),
        ),
        Index(
            "ix_class_session_room_time", "room_id", "start_at", "end_at",
            postgresql_where=text("status IN ('draft', 'published', 'paused')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("course.id", ondelete="RESTRICT"), nullable=False)
    coach_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("coach_profile.id", ondelete="RESTRICT"), nullable=False
    )
    room_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("room.id", ondelete="RESTRICT"), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    booking_open_hours_before: Mapped[int] = mapped_column(Integer, default=168, server_default="168", nullable=False)
    booking_close_minutes_before: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    cancel_cutoff_minutes_before: Mapped[int] = mapped_column(Integer, default=120, server_default="120", nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(*CLASS_SESSION_STATUSES, name="class_session_status", create_type=False),
        default="draft", server_default="draft", nullable=False,
    )
    source_session_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("class_session.id", ondelete="RESTRICT")
    )
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
