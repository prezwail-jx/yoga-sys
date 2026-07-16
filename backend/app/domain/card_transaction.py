import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base

TRANSACTION_TYPES = ("purchase", "renew", "reissue", "refund", "freeze", "unfreeze", "extend")

class CardTransaction(Base):
    __tablename__ = "card_transaction"
    __table_args__ = (
        UniqueConstraint("operator_id", "idempotency_key", name="uq_card_transaction_actor_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("member.id", ondelete="RESTRICT"), nullable=False, index=True)
    member_card_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("member_card.id", ondelete="RESTRICT"), nullable=False, index=True)
    origin_transaction_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("card_transaction.id", ondelete="RESTRICT"), nullable=True)
    source_member_card_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("member_card.id", ondelete="RESTRICT"), nullable=True)
    txn_type: Mapped[str] = mapped_column(Enum(*TRANSACTION_TYPES, name="card_transaction_type", create_type=False), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    times_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valid_days_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    operator_id: Mapped[str] = mapped_column(String(64), nullable=False)
    operator_role: Mapped[str] = mapped_column(String(32), nullable=False)
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
