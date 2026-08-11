from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.wechat_identity import WechatBindingChallenge, WechatIdentity


class WechatPersistenceError(ValueError):
    code = "wechat_persistence_error"


class WechatIdentityAlreadyBound(WechatPersistenceError):
    """The WeChat openid is already bound to a different account."""

    code = "wechat_identity_already_bound"


class WechatAccountAlreadyBound(WechatPersistenceError):
    """The account is already bound to a different WeChat openid."""

    code = "wechat_account_already_bound"


class WechatChallengeNotFound(WechatPersistenceError):
    """The binding challenge does not exist."""

    code = "binding_challenge_not_found"


class WechatChallengeConsumed(WechatPersistenceError):
    """The binding challenge has already been consumed."""

    code = "binding_challenge_consumed"


class WechatChallengeExpired(WechatPersistenceError):
    """The binding challenge has expired."""

    code = "binding_challenge_expired"


class WechatChallengeAttemptsExceeded(WechatPersistenceError):
    """Too many failed credential attempts on this challenge."""

    code = "binding_challenge_attempts_exceeded"


class WechatIdentityRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_identity(self, appid: str, openid_digest: str, *, for_update: bool = False) -> WechatIdentity | None:
        stmt = select(WechatIdentity).where(
            WechatIdentity.appid == appid,
            WechatIdentity.openid_digest == openid_digest,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.scalars(stmt).first()

    def get_identity_by_account(self, appid: str, account_id: UUID, *, for_update: bool = False) -> WechatIdentity | None:
        stmt = select(WechatIdentity).where(
            WechatIdentity.appid == appid,
            WechatIdentity.account_id == account_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.scalars(stmt).first()

    def _acquire_locks(self, *lock_keys: str) -> None:
        # A stable global order prevents two binding transactions from deadlocking.
        for lock_key in sorted(lock_keys):
            self.session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": lock_key},
            )

    def get_challenge(self, ticket_digest: str, *, for_update: bool = False) -> WechatBindingChallenge | None:
        stmt = select(WechatBindingChallenge).where(
            WechatBindingChallenge.ticket_digest == ticket_digest,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.scalars(stmt).first()

    def create_challenge(self, challenge: WechatBindingChallenge) -> WechatBindingChallenge:
        self.session.add(challenge)
        self.session.flush()
        self.session.refresh(challenge)
        return challenge

    def require_active_challenge(
        self,
        ticket_digest: str,
        *,
        now: datetime | None = None,
        max_attempts: int = 5,
        for_update: bool = True,
    ) -> WechatBindingChallenge:
        challenge = self.get_challenge(ticket_digest, for_update=for_update)
        if challenge is None:
            raise WechatChallengeNotFound("Binding challenge not found")

        current_time = now or datetime.now(timezone.utc)
        if challenge.consumed_at is not None:
            raise WechatChallengeConsumed("Binding challenge already consumed")
        if challenge.expires_at <= current_time:
            raise WechatChallengeExpired("Binding challenge expired")
        if challenge.failed_attempts >= max_attempts:
            raise WechatChallengeAttemptsExceeded("Binding challenge attempt limit reached")
        return challenge

    def increment_failed_attempts(
        self,
        ticket_digest: str,
        *,
        now: datetime | None = None,
        max_attempts: int = 5,
    ) -> int:
        # The caller must complete this transaction normally so the counter is not rolled back.
        challenge = self.require_active_challenge(
            ticket_digest,
            now=now,
            max_attempts=max_attempts,
            for_update=True,
        )
        challenge.failed_attempts += 1
        self.session.add(challenge)
        self.session.flush()
        return challenge.failed_attempts

    def bind_identity(
        self,
        ticket_digest: str,
        account_id: UUID,
        bound_by_account_id: UUID,
        bound_by_role: str,
        *,
        now: datetime | None = None,
        max_attempts: int = 5,
    ) -> WechatIdentity:
        challenge = self.require_active_challenge(
            ticket_digest,
            now=now,
            max_attempts=max_attempts,
            for_update=True,
        )
        self._acquire_locks(
            f"wechat:identity:{challenge.appid}:{challenge.openid_digest}",
            f"wechat:account:{challenge.appid}:{account_id}",
        )

        existing_by_openid = self.get_identity(challenge.appid, challenge.openid_digest, for_update=True)
        if existing_by_openid is not None:
            if existing_by_openid.account_id == account_id:
                challenge.consumed_at = now or datetime.now(timezone.utc)
                self.session.add(challenge)
                self.session.flush()
                return existing_by_openid
            raise WechatIdentityAlreadyBound("WeChat identity already bound to a different account")

        existing_by_account = self.get_identity_by_account(challenge.appid, account_id, for_update=True)
        if existing_by_account is not None:
            raise WechatAccountAlreadyBound("Account already bound to a different WeChat identity")

        bound_at = now or datetime.now(timezone.utc)
        identity = WechatIdentity(
            appid=challenge.appid,
            openid_digest=challenge.openid_digest,
            account_id=account_id,
            bound_by_account_id=bound_by_account_id,
            bound_by_role=bound_by_role,
            bound_at=bound_at,
        )
        try:
            with self.session.begin_nested():
                self.session.add(identity)
                challenge.consumed_at = bound_at
                self.session.add(challenge)
                self.session.flush()
        except IntegrityError as exc:
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            if constraint == "uq_wechat_identity_appid_openid":
                raise WechatIdentityAlreadyBound(
                    "WeChat identity already bound to a different account"
                ) from exc
            if constraint == "uq_wechat_identity_appid_account":
                raise WechatAccountAlreadyBound(
                    "Account already bound to a different WeChat identity"
                ) from exc
            raise
        self.session.refresh(identity)
        return identity

    def unbind(self, appid: str, account_id: UUID) -> WechatIdentity | None:
        self._acquire_locks(f"wechat:account:{appid}:{account_id}")
        identity = self.get_identity_by_account(appid, account_id, for_update=True)
        if identity is None:
            return None
        self.session.delete(identity)
        self.session.flush()
        return identity

    def delete_expired_challenges(self, expired_before: datetime) -> int:
        result = self.session.execute(
            delete(WechatBindingChallenge).where(
                WechatBindingChallenge.expires_at < expired_before,
            )
        )
        self.session.flush()
        return int(result.rowcount or 0)
