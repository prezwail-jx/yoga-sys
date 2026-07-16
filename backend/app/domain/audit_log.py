import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base

operator_role_type = Enum(
    "admin", "coach", "member", "system", name="operator_role", native_enum=True
)
audit_result_type = Enum(
    "success", "rejected", "failed", name="audit_result", native_enum=True
)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    operator_id: Mapped[str] = mapped_column(String(64), nullable=False)
    operator_role: Mapped[str] = mapped_column(operator_role_type, nullable=False)
    member_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[str] = mapped_column(String(64), nullable=False)
    before_state: Mapped[dict | None] = mapped_column(JSON)
    after_state: Mapped[dict | None] = mapped_column(JSON)
    result: Mapped[str] = mapped_column(audit_result_type, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
