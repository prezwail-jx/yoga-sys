from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser
from app.services.audit_log_service import AuditLogEvent, AuditLogRepository, AuditLogService

def record_audit(session: Session, *, trace_id: str, action: str, user: CurrentUser, object_type: str, object_id: str, result: str = "success", member_id: UUID | None = None, idempotency_key: str | None = None, before_state: dict[str, Any] | None = None, after_state: dict[str, Any] | None = None, reason: str | None = None) -> None:
    AuditLogService(AuditLogRepository(session)).record(AuditLogEvent(
        trace_id=trace_id, idempotency_key=idempotency_key, action=action,
        operator_id=user.user_id, operator_role=user.role, member_id=member_id,
        object_type=object_type, object_id=object_id, before_state=before_state,
        after_state=after_state, result=result, reason=reason,
    ))
