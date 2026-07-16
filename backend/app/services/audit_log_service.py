from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.audit_log import AuditLog


@dataclass(slots=True)
class AuditLogEvent:
    trace_id: str
    action: str
    operator_id: str
    operator_role: str
    object_type: str
    object_id: str
    result: str
    member_id: UUID | None = None
    idempotency_key: str | None = None
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
    reason: str | None = None
    occurred_at: datetime | None = None


class AuditLogRepository:
    def __init__(self, session: Session):
        self.session = session

    def append(self, event: AuditLogEvent) -> AuditLog:
        record = AuditLog(
            trace_id=event.trace_id,
            idempotency_key=event.idempotency_key,
            action=event.action,
            operator_id=event.operator_id,
            operator_role=event.operator_role,
            member_id=event.member_id,
            object_type=event.object_type,
            object_id=event.object_id,
            before_state=event.before_state,
            after_state=event.after_state,
            result=event.result,
            reason=event.reason,
            occurred_at=event.occurred_at or datetime.now(timezone.utc),
        )
        self.session.add(record)
        self.session.flush()
        return record


class AuditLogService:
    def __init__(self, repository: AuditLogRepository):
        self.repository = repository

    def record(self, event: AuditLogEvent) -> AuditLog:
        return self.repository.append(event)
