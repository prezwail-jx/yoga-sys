import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base

WRITE_OFF_EVENT_TYPES = ("reserve_hold", "checkin_commit", "cancel_refund", "absence_commit")
TERMINAL_EVENT_TYPES = ("checkin_commit", "cancel_refund", "absence_commit")

class WriteOffEvent(Base):
    __tablename__ = "writeoff_event"
    __table_args__ = (
        UniqueConstraint("business_ref", "event_type", name="uq_writeoff_business_event"),
        CheckConstraint("sequence_no IN (1, 2)", name="ck_writeoff_sequence"),
        CheckConstraint(
            "(event_type = 'reserve_hold' AND sequence_no = 1 AND previous_event_id IS NULL) OR "
            "(event_type <> 'reserve_hold' AND sequence_no = 2 AND previous_event_id IS NOT NULL)",
            name="ck_writeoff_lifecycle_shape",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("member.id", ondelete="RESTRICT"), nullable=False)
    member_card_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("member_card.id", ondelete="RESTRICT"), nullable=False)
    previous_event_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("writeoff_event.id", ondelete="RESTRICT"))
    event_type: Mapped[str] = mapped_column(Enum(*WRITE_OFF_EVENT_TYPES, name="writeoff_event_type", create_type=False), nullable=False)
    business_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    times_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    selection_basis: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    operator_id: Mapped[str] = mapped_column(String(64), nullable=False)
    operator_role: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
