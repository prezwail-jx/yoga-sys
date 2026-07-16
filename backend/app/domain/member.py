import uuid
from datetime import datetime, date
from uuid import UUID

from sqlalchemy import String, Date, Text, DateTime, func, text, Enum, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base

class Member(Base):
    __tablename__ = "member"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    birthday: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    join_date: Mapped[date] = mapped_column(Date, nullable=False)
    emergency_contact: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    status: Mapped[str] = mapped_column(
        Enum('normal', 'paused', 'expired', 'disabled', name='member_status', create_type=False),
        nullable=False,
        default='normal',
        index=True
    )
    
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
