from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.wechat_config import WechatConfig
from app.repositories.admin_user import AdminUserRepository
from app.repositories.wechat_identity import WechatIdentityRepository
from app.schemas.account_binding import WechatBindingStatusResponse
from app.services.audit_log_service import AuditLogEvent, AuditLogRepository, AuditLogService


class AuditActor(Protocol):
    user_id: str
    role: str


class ManagedAccountNotFoundError(ValueError):
    pass


class WechatBindingNotFoundError(ValueError):
    pass


class WechatBindingRecoveryService:
    def __init__(self, session: Session, config: WechatConfig) -> None:
        self.account_repo = AdminUserRepository(session)
        self.identity_repo = WechatIdentityRepository(session)
        self.config = config
        self.audit = AuditLogService(AuditLogRepository(session))

    def get_status(self, account_id: UUID) -> WechatBindingStatusResponse:
        self._require_member_or_coach(account_id)
        identity = self.identity_repo.get_identity_by_account(self.config.app_id, account_id)
        return WechatBindingStatusResponse(
            account_id=account_id,
            bound=identity is not None,
            bound_at=identity.bound_at if identity is not None else None,
        )

    def unbind(self, account_id: UUID, *, actor: AuditActor, trace_id: str) -> None:
        account = self._require_member_or_coach(account_id)
        identity = self.identity_repo.unbind(self.config.app_id, account.id)
        if identity is None:
            raise WechatBindingNotFoundError("WeChat binding not found")

        self.audit.record(
            AuditLogEvent(
                trace_id=trace_id,
                action="wechat_binding_unbind",
                operator_id=actor.user_id,
                operator_role=actor.role,
                member_id=account.member_id,
                object_type="admin_user",
                object_id=str(account.id),
                result="success",
                after_state={"role": account.role, "wechatBound": False},
            )
        )

    def _require_member_or_coach(self, account_id: UUID):
        account = self.account_repo.get_by_id(account_id)
        if account is None or account.role not in {"member", "coach"}:
            raise ManagedAccountNotFoundError("Managed account not found")
        return account
