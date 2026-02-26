from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(slots=True)
class AuditLogEvent:
    trace_id: str
    action: str
    operator_id: str
    operator_role: str
    object_type: str
    object_id: str
    result: str
    member_id: str | None = None
    idempotency_key: str | None = None
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
    reason: str | None = None
    occurred_at: datetime | None = None


class AuditLogRepository:
    def __init__(self, session: Session):
        self.session = session

    def append(self, event: AuditLogEvent) -> None:
        self.session.execute(
            text(
                """
                INSERT INTO audit_log (
                    trace_id, idempotency_key, action, operator_id, operator_role,
                    member_id, object_type, object_id, before_state, after_state,
                    result, reason, occurred_at
                ) VALUES (
                    :trace_id, :idempotency_key, :action, :operator_id, :operator_role,
                    CAST(:member_id AS uuid), :object_type, :object_id, :before_state::jsonb,
                    :after_state::jsonb, :result, :reason, :occurred_at
                )
                """
            ),
            {
                "trace_id": event.trace_id,
                "idempotency_key": event.idempotency_key,
                "action": event.action,
                "operator_id": event.operator_id,
                "operator_role": event.operator_role,
                "member_id": event.member_id,
                "object_type": event.object_type,
                "object_id": event.object_id,
                "before_state": event.before_state,
                "after_state": event.after_state,
                "result": event.result,
                "reason": event.reason,
                "occurred_at": event.occurred_at or datetime.now(timezone.utc),
            },
        )


class AuditLogService:
    def __init__(self, repository: AuditLogRepository):
        self.repository = repository

    def record(self, event: AuditLogEvent) -> None:
        self.repository.append(event)
