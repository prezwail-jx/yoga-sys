import uuid
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import String, Numeric, Integer, Boolean, DateTime, func, Enum, Uuid, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base

class CardProduct(Base):
    __tablename__ = "card_product"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    card_type: Mapped[str] = mapped_column(
        Enum('duration', 'times', 'private', 'trial', name='card_type', create_type=False),
        nullable=False
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cost_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    total_times: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valid_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    activation_mode: Mapped[str] = mapped_column(
        Enum('immediate', 'first_booking', name='activation_mode', create_type=False),
        nullable=False
    )
    applicable_course_scope: Mapped[str] = mapped_column(
        Enum('group', 'private', 'specific', name='course_scope', create_type=False),
        nullable=False
    )
    specific_course_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    
    absence_deduct_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cancel_refund_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
