import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import String, DateTime, func, text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base

class AdminUser(Base):
    __tablename__ = "admin_user"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
