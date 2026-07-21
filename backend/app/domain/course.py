import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, Index, Integer, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base


COURSE_DIFFICULTIES = ("all_levels", "beginner", "intermediate", "advanced")


class Course(Base):
    __tablename__ = "course"
    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="ck_course_duration_positive"),
        Index("uq_course_name_lower", text("lower(name)"), unique=True),
        Index("ix_course_enabled_name", "enabled", "name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[str] = mapped_column(
        Enum(*COURSE_DIFFICULTIES, name="course_difficulty", create_type=False), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    cover_url: Mapped[str | None] = mapped_column(String(512))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
