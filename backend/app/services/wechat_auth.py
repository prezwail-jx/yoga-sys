from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.wechat_config import WechatConfig
from app.domain.wechat_identity import WechatBindingChallenge
from app.integrations.wechat import (
    WechatCodeExchangeProvider,
    WechatCodeInvalidError,
    WechatLoginRejectedError,
    WechatProviderBusyError,
    WechatProviderConfigError,
    WechatProviderError,
    WechatProviderInvalidResponseError,
    WechatProviderRateLimitedError,
    WechatProviderTimeoutError,
    WechatProviderUnavailableError,
    generate_binding_challenge,
    wechat_ticket_digest,
)
from app.repositories.admin_user import AdminUserRepository
from app.repositories.wechat_identity import (
    WechatAccountAlreadyBound,
    WechatChallengeAttemptsExceeded,
    WechatChallengeConsumed,
    WechatChallengeExpired,
    WechatChallengeNotFound,
    WechatIdentityAlreadyBound,
    WechatIdentityRepository,
)
from app.schemas.wechat_auth import (
    WechatAuthErrorResponse,
    WechatBindRequest,
    WechatBindResponse,
    WechatErrorCode,
    WechatSessionRequest,
    WechatSessionResponse,
)
from app.services.audit_log_service import AuditLogEvent, AuditLogRepository, AuditLogService
from app.services.auth import AccountIneligibleError, AuthService
from app.services.rate_limit import SlidingWindowRateLimiter


@dataclass(frozen=True)
class WechatAuthOutcome:
    status_code: int
    body: WechatSessionResponse | WechatBindResponse | WechatAuthErrorResponse


class WechatAuthService:
    def __init__(
        self,
        session: Session,
        config: WechatConfig,
        provider: WechatCodeExchangeProvider,
        auth_service: AuthService,
        rate_limiter: SlidingWindowRateLimiter,
    ) -> None:
        self.session = session
        self.config = config
        self.provider = provider
        self.auth_service = auth_service
        self.identity_repo = WechatIdentityRepository(session)
        self.account_repo = AdminUserRepository(session)
        self.rate_limiter = rate_limiter
        self.audit = AuditLogService(AuditLogRepository(session))

    def start_session(
        self,
        payload: WechatSessionRequest,
        *,
        client_ip: str,
        user_agent: str,
        trace_id: str,
    ) -> WechatAuthOutcome:
        if not self.config.auth_enabled:
            return self._session_error(404, WechatErrorCode.AUTH_DISABLED, "WeChat authentication is disabled")

        try:
            provider_session = self.provider.exchange(payload.code)
        except WechatProviderError as exc:
            status_code, code, description = self._provider_error(exc)
            self._audit(trace_id, "wechat_session_rejected", "wechat-session", "rejected", code)
            return self._session_error(status_code, code, description)

        raw_ticket, ticket_digest, openid_digest, source_fingerprint, expires_at = generate_binding_challenge(
            self.config,
            self.config.app_id,
            provider_session.openid,
            client_ip,
            user_agent,
        )
        # Serializes JWT issuance with an administrator unbind of this identity.
        identity = self.identity_repo.get_identity(self.config.app_id, openid_digest, for_update=True)
        if identity is not None:
            account = self.account_repo.get_by_id(identity.account_id)
            if account is None:
                self._audit(trace_id, "wechat_session_rejected", str(identity.id), "rejected", "account_missing")
                return self._session_error(403, WechatErrorCode.ACCOUNT_DISABLED, "Account is unavailable")
            try:
                login = self.auth_service.issue_token_for_account(account)
            except AccountIneligibleError:
                self._audit(trace_id, "wechat_session_rejected", str(identity.id), "rejected", "account_ineligible")
                return self._session_error(403, WechatErrorCode.ACCOUNT_DISABLED, "Account is unavailable")
            return WechatAuthOutcome(
                200,
                WechatSessionResponse(
                    state="bound",
                    access_token=login.access_token,
                    token_type=login.token_type,
                    role=login.role,
                ),
            )

        self.identity_repo.delete_expired_challenges(datetime.now(timezone.utc))
        challenge = WechatBindingChallenge(
            ticket_digest=ticket_digest,
            appid=self.config.app_id,
            openid_digest=openid_digest,
            expires_at=expires_at,
            source_fingerprint=source_fingerprint,
        )
        self.identity_repo.create_challenge(challenge)
        return WechatAuthOutcome(
            200,
            WechatSessionResponse(
                state="binding_required",
                binding_ticket=raw_ticket,
                expires_in=int(timedelta(minutes=self.config.binding_challenge_minutes).total_seconds()),
            ),
        )

    def bind(
        self,
        payload: WechatBindRequest,
        *,
        trace_id: str,
    ) -> WechatAuthOutcome:
        ticket_digest = wechat_ticket_digest(self.config, payload.binding_ticket)
        try:
            challenge = self.identity_repo.require_active_challenge(
                ticket_digest,
                max_attempts=self.config.binding_max_attempts,
            )
        except (WechatChallengeNotFound, WechatChallengeConsumed, WechatChallengeExpired, WechatChallengeAttemptsExceeded) as exc:
            return self._challenge_error(exc, trace_id)

        rate_key = f"wechat-bind:{challenge.source_fingerprint}"
        if not self.rate_limiter.allow(
            rate_key,
            limit=self.config.binding_source_max_attempts,
            window_seconds=self.config.binding_source_window_seconds,
        ):
            self._audit(trace_id, "wechat_binding_ticket_abuse", str(challenge.id), "rejected", "source_rate_limited")
            return self._bind_error(429, WechatErrorCode.CHALLENGE_ATTEMPTS_EXCEEDED, "Too many attempts")

        account = self.auth_service.authenticate_credentials(payload.username, payload.password)
        if account is None:
            self.identity_repo.increment_failed_attempts(
                ticket_digest, max_attempts=self.config.binding_max_attempts
            )
            self._audit(trace_id, "wechat_binding_credentials_rejected", str(challenge.id), "rejected", "invalid_credentials")
            return self._bind_error(401, WechatErrorCode.BINDING_CREDENTIALS_REJECTED, "Invalid credentials")

        if account.role == "admin":
            self.identity_repo.increment_failed_attempts(
                ticket_digest, max_attempts=self.config.binding_max_attempts
            )
            self._audit(trace_id, "wechat_binding_admin_rejected", str(challenge.id), "rejected", "admin_role")
            return self._bind_error(401, WechatErrorCode.BINDING_CREDENTIALS_REJECTED, "Invalid credentials")

        try:
            login = self.auth_service.issue_token_for_account(account)
        except AccountIneligibleError:
            self.identity_repo.increment_failed_attempts(
                ticket_digest, max_attempts=self.config.binding_max_attempts
            )
            self._audit(trace_id, "wechat_binding_account_disabled", str(challenge.id), "rejected", "account_ineligible")
            return self._bind_error(401, WechatErrorCode.BINDING_CREDENTIALS_REJECTED, "Invalid credentials")

        try:
            identity = self.identity_repo.bind_identity(
                ticket_digest,
                account.id,
                account.id,
                account.role,
                max_attempts=self.config.binding_max_attempts,
            )
        except (WechatIdentityAlreadyBound, WechatAccountAlreadyBound):
            self._audit(trace_id, "wechat_binding_conflict", str(challenge.id), "rejected", "binding_conflict")
            return self._bind_error(409, WechatErrorCode.BINDING_CONFLICT, "WeChat identity is already bound")

        self._audit(
            trace_id,
            "wechat_binding_success",
            str(identity.id),
            "success",
            None,
            after_state={"accountId": str(account.id), "role": account.role},
        )
        return WechatAuthOutcome(200, WechatBindResponse(access_token=login.access_token, role=login.role))

    def _challenge_error(self, exc: Exception, trace_id: str) -> WechatAuthOutcome:
        mapping = {
            WechatChallengeNotFound: (404, WechatErrorCode.CHALLENGE_NOT_FOUND, "Binding ticket was not found"),
            WechatChallengeConsumed: (409, WechatErrorCode.CHALLENGE_CONSUMED, "Binding ticket was already used"),
            WechatChallengeExpired: (410, WechatErrorCode.CHALLENGE_EXPIRED, "Binding ticket has expired"),
            WechatChallengeAttemptsExceeded: (429, WechatErrorCode.CHALLENGE_ATTEMPTS_EXCEEDED, "Too many attempts"),
        }
        status_code, code, description = mapping[type(exc)]
        self._audit(trace_id, "wechat_binding_ticket_abuse", "binding-ticket", "rejected", code)
        return self._bind_error(status_code, code, description)

    @staticmethod
    def _provider_error(exc: WechatProviderError) -> tuple[int, str, str]:
        if isinstance(exc, WechatCodeInvalidError):
            return 401, WechatErrorCode.CODE_INVALID, "WeChat login code is invalid or expired"
        if isinstance(exc, WechatProviderRateLimitedError):
            return 503, WechatErrorCode.PROVIDER_RATE_LIMITED, "WeChat service is rate limited"
        if isinstance(exc, WechatLoginRejectedError):
            return 403, WechatErrorCode.LOGIN_REJECTED, "WeChat login was rejected"
        if isinstance(exc, WechatProviderTimeoutError):
            return 504, WechatErrorCode.PROVIDER_TIMEOUT, "WeChat service timed out"
        if isinstance(exc, (WechatProviderUnavailableError, WechatProviderBusyError)):
            return 502, WechatErrorCode.PROVIDER_UNAVAILABLE, "WeChat service is unavailable"
        if isinstance(exc, (WechatProviderConfigError, WechatProviderInvalidResponseError)):
            return 502, WechatErrorCode.PROVIDER_INVALID_RESPONSE, "WeChat service returned an invalid response"
        return 502, WechatErrorCode.PROVIDER_UNAVAILABLE, "WeChat service is unavailable"

    @staticmethod
    def _session_error(status_code: int, code: str, description: str) -> WechatAuthOutcome:
        return WechatAuthOutcome(
            status_code,
            WechatSessionResponse(state="error", error=code, error_description=description),
        )

    @staticmethod
    def _bind_error(status_code: int, code: str, description: str) -> WechatAuthOutcome:
        return WechatAuthOutcome(status_code, WechatAuthErrorResponse(error=code, error_description=description))

    def _audit(
        self,
        trace_id: str,
        action: str,
        object_id: str,
        result: str,
        reason: str | None,
        *,
        after_state: dict[str, str] | None = None,
    ) -> None:
        self.audit.record(
            AuditLogEvent(
                trace_id=trace_id,
                action=action,
                operator_id="wechat-auth",
                operator_role="system",
                object_type="wechat_identity",
                object_id=object_id,
                result=result,
                reason=reason,
                after_state=after_state,
            )
        )
