import hashlib
import hmac
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.admin_user import AdminUser
from app.domain.member import Member
from app.domain.wechat_identity import WechatBindingChallenge, WechatIdentity
from app.repositories.wechat_identity import (
    WechatAccountAlreadyBound,
    WechatChallengeAttemptsExceeded,
    WechatChallengeConsumed,
    WechatChallengeExpired,
    WechatIdentityAlreadyBound,
    WechatIdentityRepository,
    WechatPersistenceError,
)


NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
APPID = "wx-test-app"
PEPPER = b"test-only-pepper"


def _digest(value: str) -> str:
    return hmac.new(PEPPER, value.encode(), hashlib.sha256).hexdigest()


def _challenge(
    ticket: str,
    openid: str,
    *,
    appid: str = APPID,
    expires_at: datetime | None = None,
) -> WechatBindingChallenge:
    return WechatBindingChallenge(
        ticket_digest=_digest(ticket),
        appid=appid,
        openid_digest=_digest(f"{appid}:{openid}"),
        expires_at=expires_at or NOW + timedelta(minutes=10),
        source_fingerprint=_digest("127.0.0.1:test-agent"),
    )


def _member_account(session: Session, suffix: str | None = None) -> tuple[Member, AdminUser]:
    suffix = suffix or uuid4().hex[:10]
    member_id = uuid4()
    member = Member(
        id=member_id,
        name=f"微信测试会员-{suffix}",
        phone=f"13{member_id.int % 1_000_000_000:09d}",
        join_date=date(2030, 1, 1),
        status="normal",
    )
    account = AdminUser(
        id=uuid4(),
        username=f"wechat-{suffix}",
        password_hash="test-hash",
        role="member",
        member_id=member.id,
    )
    session.add(member)
    session.flush()
    session.add(account)
    session.flush()
    return member, account


@pytest.mark.integration
def test_challenge_creation_binding_and_same_pair_idempotency(db):
    member, account = _member_account(db)
    repo = WechatIdentityRepository(db)
    first_challenge = repo.create_challenge(_challenge("ticket-1", "openid-1"))

    identity = repo.bind_identity(
        first_challenge.ticket_digest,
        account.id,
        account.id,
        "member",
        now=NOW,
    )

    assert identity.account_id == account.id
    assert identity.bound_by_account_id == account.id
    assert identity.bound_at == NOW
    assert account.member_id == member.id
    assert repo.get_challenge(first_challenge.ticket_digest).consumed_at == NOW

    second_challenge = repo.create_challenge(_challenge("ticket-2", "openid-1"))
    replay = repo.bind_identity(
        second_challenge.ticket_digest,
        account.id,
        account.id,
        "member",
        now=NOW + timedelta(seconds=1),
    )
    assert replay.id == identity.id
    assert repo.get_challenge(second_challenge.ticket_digest).consumed_at is not None


@pytest.mark.integration
def test_identity_and_account_conflicts_are_deterministic(db):
    _, account_a = _member_account(db)
    _, account_b = _member_account(db)
    repo = WechatIdentityRepository(db)

    first = repo.create_challenge(_challenge("identity-first", "shared-openid"))
    repo.bind_identity(first.ticket_digest, account_a.id, account_a.id, "member", now=NOW)

    identity_conflict = repo.create_challenge(_challenge("identity-conflict", "shared-openid"))
    with pytest.raises(WechatIdentityAlreadyBound) as identity_error:
        repo.bind_identity(
            identity_conflict.ticket_digest,
            account_b.id,
            account_b.id,
            "member",
            now=NOW,
        )
    assert identity_error.value.code == "wechat_identity_already_bound"

    account_conflict = repo.create_challenge(_challenge("account-conflict", "other-openid"))
    with pytest.raises(WechatAccountAlreadyBound) as account_error:
        repo.bind_identity(
            account_conflict.ticket_digest,
            account_a.id,
            account_a.id,
            "member",
            now=NOW,
        )
    assert account_error.value.code == "wechat_account_already_bound"


@pytest.mark.integration
def test_bindings_are_isolated_by_appid(db):
    _, account = _member_account(db)
    repo = WechatIdentityRepository(db)
    first = repo.create_challenge(_challenge("app-a-ticket", "same-openid", appid="app-a"))
    second = repo.create_challenge(_challenge("app-b-ticket", "same-openid", appid="app-b"))

    identity_a = repo.bind_identity(first.ticket_digest, account.id, account.id, "member", now=NOW)
    identity_b = repo.bind_identity(second.ticket_digest, account.id, account.id, "member", now=NOW)

    assert identity_a.id != identity_b.id
    assert {identity_a.appid, identity_b.appid} == {"app-a", "app-b"}


@pytest.mark.integration
def test_consumed_expired_and_attempt_limited_challenges_are_rejected(db):
    _, account = _member_account(db)
    repo = WechatIdentityRepository(db)

    consumed = repo.create_challenge(_challenge("consumed-ticket", "consumed-openid"))
    repo.bind_identity(consumed.ticket_digest, account.id, account.id, "member", now=NOW)
    with pytest.raises(WechatChallengeConsumed):
        repo.bind_identity(consumed.ticket_digest, account.id, account.id, "member", now=NOW)

    expired = repo.create_challenge(_challenge("expired-ticket", "expired-openid"))
    with pytest.raises(WechatChallengeExpired):
        repo.bind_identity(
            expired.ticket_digest,
            account.id,
            account.id,
            "member",
            now=NOW + timedelta(minutes=11),
        )

    limited = repo.create_challenge(_challenge("limited-ticket", "limited-openid"))
    for expected in range(1, 6):
        assert repo.increment_failed_attempts(limited.ticket_digest, now=NOW) == expected
    with pytest.raises(WechatChallengeAttemptsExceeded):
        repo.bind_identity(limited.ticket_digest, account.id, account.id, "member", now=NOW)


@pytest.mark.integration
def test_unbind_allows_standard_rebinding(db):
    _, account = _member_account(db)
    repo = WechatIdentityRepository(db)
    first = repo.create_challenge(_challenge("unbind-first", "openid-first"))
    repo.bind_identity(first.ticket_digest, account.id, account.id, "member", now=NOW)

    removed = repo.unbind(APPID, account.id)
    assert removed is not None
    assert repo.get_identity_by_account(APPID, account.id) is None

    second = repo.create_challenge(_challenge("unbind-second", "openid-second"))
    rebound = repo.bind_identity(second.ticket_digest, account.id, account.id, "member", now=NOW)
    assert rebound.openid_digest == second.openid_digest


@pytest.mark.integration
def test_expiry_cleanup_removes_consumed_and_unconsumed_challenges(db):
    _, account = _member_account(db)
    repo = WechatIdentityRepository(db)
    consumed = repo.create_challenge(_challenge("cleanup-consumed", "cleanup-openid"))
    pending = repo.create_challenge(_challenge("cleanup-pending", "cleanup-pending-openid"))
    repo.bind_identity(consumed.ticket_digest, account.id, account.id, "member", now=NOW)

    deleted = repo.delete_expired_challenges(NOW + timedelta(hours=1))

    assert deleted >= 2
    assert repo.get_challenge(consumed.ticket_digest) is None
    assert repo.get_challenge(pending.ticket_digest) is None


@pytest.mark.integration
def test_schema_rejects_invalid_digests_roles_and_sources(db):
    _, account = _member_account(db)

    invalid_challenge = _challenge("invalid-ticket", "invalid-openid")
    invalid_challenge.ticket_digest = "short"
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(invalid_challenge)
            db.flush()

    invalid_source = _challenge("invalid-source", "invalid-source-openid")
    invalid_source.source_fingerprint = "raw-ip"
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(invalid_source)
            db.flush()

    invalid_identity = WechatIdentity(
        appid=APPID,
        openid_digest=_digest("invalid-role-openid"),
        account_id=account.id,
        bound_by_account_id=account.id,
        bound_by_role="admin",
        bound_at=NOW,
    )
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(invalid_identity)
            db.flush()


@pytest.mark.integration
def test_schema_contains_only_digest_fields_for_wechat_material(db):
    identity_columns = set(WechatIdentity.__table__.columns.keys())
    challenge_columns = set(WechatBindingChallenge.__table__.columns.keys())
    all_columns = identity_columns | challenge_columns

    assert "openid" not in all_columns
    assert "session_key" not in all_columns
    assert "ticket" not in all_columns
    assert {"openid_digest", "ticket_digest"} <= all_columns

    inspector = inspect(db.get_bind())
    identity_constraints = {
        constraint["name"] for constraint in inspector.get_unique_constraints("wechat_identity")
    }
    assert identity_constraints == {
        "uq_wechat_identity_appid_openid",
        "uq_wechat_identity_appid_account",
    }


@dataclass
class CommittedBindingScenario:
    appid: str
    member_ids: list[UUID]
    account_ids: list[UUID]
    ticket_digests: list[str]


@pytest.fixture
def committed_binding_scenario(db_engine):
    scenarios: list[CommittedBindingScenario] = []

    def create(*, account_count: int, openids: list[str]) -> CommittedBindingScenario:
        suffix = uuid4().hex[:10]
        appid = f"wx-concurrency-{suffix}"
        ticket_digests: list[str] = []
        with Session(db_engine, expire_on_commit=False) as session:
            accounts = [_member_account(session, f"{suffix}{index}") for index in range(account_count)]
            for index, openid in enumerate(openids):
                challenge = _challenge(
                    f"{suffix}-ticket-{index}",
                    openid,
                    appid=appid,
                )
                session.add(challenge)
                session.flush()
                ticket_digests.append(challenge.ticket_digest)
            session.commit()

        scenario = CommittedBindingScenario(
            appid=appid,
            member_ids=[member.id for member, _ in accounts],
            account_ids=[account.id for _, account in accounts],
            ticket_digests=ticket_digests,
        )
        scenarios.append(scenario)
        return scenario

    yield create

    with Session(db_engine) as session:
        for scenario in reversed(scenarios):
            session.execute(delete(WechatIdentity).where(WechatIdentity.appid == scenario.appid))
            session.execute(
                delete(WechatBindingChallenge).where(
                    WechatBindingChallenge.appid == scenario.appid
                )
            )
            session.execute(delete(AdminUser).where(AdminUser.id.in_(scenario.account_ids)))
            session.execute(delete(Member).where(Member.id.in_(scenario.member_ids)))
        session.commit()


def _concurrent_bind(
    db_engine,
    barrier: Barrier,
    ticket_digest: str,
    account_id: UUID,
) -> str:
    barrier.wait()
    with Session(db_engine) as session:
        try:
            WechatIdentityRepository(session).bind_identity(
                ticket_digest,
                account_id,
                account_id,
                "member",
                now=NOW,
            )
            session.commit()
            return "success"
        except WechatPersistenceError as exc:
            session.rollback()
            return exc.code


@pytest.mark.integration
def test_concurrent_same_openid_allows_one_account(
    db_engine,
    committed_binding_scenario,
):
    scenario = committed_binding_scenario(account_count=2, openids=["same", "same"])
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda args: _concurrent_bind(db_engine, barrier, *args),
                zip(scenario.ticket_digests, scenario.account_ids),
            )
        )

    assert sorted(results) == ["success", "wechat_identity_already_bound"]
    with Session(db_engine) as session:
        count = session.scalar(
            select(func.count()).select_from(WechatIdentity).where(
                WechatIdentity.appid == scenario.appid
            )
        )
    assert count == 1


@pytest.mark.integration
def test_concurrent_same_account_allows_one_openid(
    db_engine,
    committed_binding_scenario,
):
    scenario = committed_binding_scenario(account_count=1, openids=["openid-a", "openid-b"])
    barrier = Barrier(2)
    args = [(ticket, scenario.account_ids[0]) for ticket in scenario.ticket_digests]
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda values: _concurrent_bind(db_engine, barrier, *values),
                args,
            )
        )

    assert sorted(results) == ["success", "wechat_account_already_bound"]


@pytest.mark.integration
def test_concurrent_same_ticket_is_consumed_once(
    db_engine,
    committed_binding_scenario,
):
    scenario = committed_binding_scenario(account_count=1, openids=["one-openid"])
    barrier = Barrier(2)
    args = [(scenario.ticket_digests[0], scenario.account_ids[0])] * 2
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda values: _concurrent_bind(db_engine, barrier, *values),
                args,
            )
        )

    assert sorted(results) == ["binding_challenge_consumed", "success"]


@pytest.mark.integration
def test_failed_attempt_count_persists_after_commit(db_engine, committed_binding_scenario):
    scenario = committed_binding_scenario(account_count=1, openids=["attempt-openid"])
    with Session(db_engine) as session:
        count = WechatIdentityRepository(session).increment_failed_attempts(
            scenario.ticket_digests[0],
            now=NOW,
        )
        session.commit()
    assert count == 1

    with Session(db_engine) as session:
        challenge = WechatIdentityRepository(session).get_challenge(scenario.ticket_digests[0])
        assert challenge.failed_attempts == 1
