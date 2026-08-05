from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.services.audit_log_service import AuditLogEvent, AuditLogRepository, AuditLogService

if TYPE_CHECKING:
    from app.api.deps.auth import CurrentUser

def record_audit(session: Session, *, trace_id: str, action: str, user: CurrentUser, object_type: str, object_id: str, result: str = "success", member_id: UUID | None = None, idempotency_key: str | None = None, before_state: dict[str, Any] | None = None, after_state: dict[str, Any] | None = None, reason: str | None = None):
    return AuditLogService(AuditLogRepository(session)).record(AuditLogEvent(
        trace_id=trace_id, idempotency_key=idempotency_key, action=action,
        operator_id=user.user_id, operator_role=user.role, member_id=member_id,
        object_type=object_type, object_id=object_id,
        before_state=jsonable_encoder(before_state) if before_state is not None else None,
        after_state=jsonable_encoder(after_state) if after_state is not None else None,
        result=result, reason=reason,
    ))
