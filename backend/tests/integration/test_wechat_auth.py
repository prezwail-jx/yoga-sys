from dataclasses import replace
from datetime import date
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_wechat_auth_service
from app.core.security import ALGORITHM, SECRET_KEY, get_password_hash
from app.core.wechat_config import WechatConfig
from app.domain.admin_user import AdminUser
from app.domain.audit_log import AuditLog
from app.domain.coach_profile import CoachProfile
from app.domain.member import Member
from app.integrations.wechat import FakeWechatProvider, WechatCodeInvalidError, wechat_ticket_digest
from app.main import app
from app.repositories.admin_user import AdminUserRepository
from app.repositories.wechat_identity import WechatIdentityRepository
from app.services.auth import AuthService
from app.services.rate_limit import SlidingWindowRateLimiter
from app.services.wechat_auth import WechatAuthService


class InvalidCodeProvider:
    def exchange(self, code: str):
        raise WechatCodeInvalidError("invalid")


@pytest.fixture
def wechat_client(db):
    config = WechatConfig.for_tests(app_id=f"wx-auth-{uuid4().hex[:12]}", identity_pepper="p" * 32)
    service = WechatAuthService(
        db,
        config,
        FakeWechatProvider(config.app_id),
        AuthService(AdminUserRepository(db)),
        SlidingWindowRateLimiter(),
    )
    app.dependency_overrides[get_wechat_auth_service] = lambda: service
    with TestClient(app) as client:
        yield client, service
    app.dependency_overrides.clear()


def _member_account(db, *, status: str = "normal") -> AdminUser:
    suffix = uuid4().hex[:12]
    member = Member(
        name=f"Wechat Member {suffix}",
        phone=f"13{uuid4().int % 1_000_000_000:09d}",
        join_date=date(2026, 8, 6),
        status=status,
    )
    db.add(member)
    db.flush()
    account = AdminUser(
        username=f"member-{suffix}",
        password_hash=get_password_hash("secret123"),
        role="member",
        member_id=member.id,
    )
    db.add(account)
    db.flush()
    return account


def _coach_account(db, *, enabled: bool = True) -> AdminUser:
    suffix = uuid4().hex[:12]
    coach = CoachProfile(name=f"Wechat Coach {suffix}", enabled=enabled)
    db.add(coach)
    db.flush()
    account = AdminUser(
        username=f"coach-{suffix}",
        password_hash=get_password_hash("secret123"),
        role="coach",
        coach_profile_id=coach.id,
    )
    db.add(account)
    db.flush()
    return account


def _start_binding(client: TestClient, code: str) -> str:
    response = client.post("/auth/wechat/session", json={"code": code})
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "binding_required"
    assert "accessToken" not in body
    return body["bindingTicket"]


@pytest.mark.integration
def test_unbound_session_returns_only_a_binding_ticket(wechat_client, db):
    client, service = wechat_client
    ticket = _start_binding(client, "first-code")

    challenge = WechatIdentityRepository(db).get_challenge(wechat_ticket_digest(service.config, ticket))
    assert challenge is not None
    assert challenge.appid == service.config.app_id
    assert challenge.consumed_at is None


@pytest.mark.integration
def test_member_binding_issues_standard_member_jwt_and_can_log_in_again(wechat_client, db):
    client, service = wechat_client
    account = _member_account(db)
    ticket = _start_binding(client, "fake:member-code:one")

    bound = client.post(
        "/auth/wechat/bind",
        json={"bindingTicket": ticket, "username": account.username.upper(), "password": "secret123"},
    )
    assert bound.status_code == 200
    claims = jwt.decode(bound.json()["accessToken"], SECRET_KEY, algorithms=[ALGORITHM])
    assert claims["role"] == "member"
    assert claims["memberId"] == str(account.member_id)

    repeat = client.post("/auth/wechat/session", json={"code": "fake:member-code:two"})
    assert repeat.status_code == 200
    assert repeat.json()["state"] == "bound"
    assert "bindingTicket" not in repeat.json()

    replay = client.post(
        "/auth/wechat/bind",
        json={"bindingTicket": ticket, "username": account.username, "password": "secret123"},
    )
    assert replay.status_code == 409
    assert replay.json()["error"] == "binding_challenge_consumed"


@pytest.mark.integration
def test_coach_binding_issues_standard_coach_jwt(wechat_client, db):
    client, _ = wechat_client
    account = _coach_account(db)
    ticket = _start_binding(client, "coach-code")

    bound = client.post(
        "/auth/wechat/bind",
        json={"bindingTicket": ticket, "username": account.username, "password": "secret123"},
    )
    claims = jwt.decode(bound.json()["accessToken"], SECRET_KEY, algorithms=[ALGORITHM])
    assert claims["role"] == "coach"
    assert claims["coachProfileId"] == str(account.coach_profile_id)


@pytest.mark.integration
def test_invalid_credentials_increment_attempts_and_commit(wechat_client, db):
    client, service = wechat_client
    ticket = _start_binding(client, "wrong-password")
    response = client.post(
        "/auth/wechat/bind",
        json={"bindingTicket": ticket, "username": "missing", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["error"] == "binding_credentials_rejected"

    challenge = WechatIdentityRepository(db).get_challenge(wechat_ticket_digest(service.config, ticket))
    assert challenge.failed_attempts == 1
    assert challenge.consumed_at is None


@pytest.mark.integration
def test_admin_and_disabled_accounts_are_rejected_without_binding(wechat_client, db):
    client, _ = wechat_client
    disabled_account = _member_account(db, status="disabled")
    disabled_ticket = _start_binding(client, "disabled-member")
    disabled = client.post(
        "/auth/wechat/bind",
        json={"bindingTicket": disabled_ticket, "username": disabled_account.username, "password": "secret123"},
    )
    assert disabled.status_code == 401

    admin_ticket = _start_binding(client, "admin-account")
    admin = client.post(
        "/auth/wechat/bind",
        json={"bindingTicket": admin_ticket, "username": "admin", "password": "admin123"},
    )
    assert admin.status_code == 401
    assert WechatIdentityRepository(db).get_identity_by_account(
        wechat_client[1].config.app_id, disabled_account.id
    ) is None


@pytest.mark.integration
def test_bound_disabled_coach_returns_actionable_error(wechat_client, db):
    client, _ = wechat_client
    account = _coach_account(db, enabled=True)
    ticket = _start_binding(client, "coach-disabled")
    assert client.post(
        "/auth/wechat/bind",
        json={"bindingTicket": ticket, "username": account.username, "password": "secret123"},
    ).status_code == 200
    db.get(CoachProfile, account.coach_profile_id).enabled = False
    db.flush()

    response = client.post("/auth/wechat/session", json={"code": "coach-disabled"})
    assert response.status_code == 403
    assert response.json()["error"] == "account_disabled"


@pytest.mark.integration
def test_invalid_code_is_rejected_without_persisting_challenge(wechat_client, db):
    client, service = wechat_client
    service.provider = InvalidCodeProvider()

    response = client.post("/auth/wechat/session", json={"code": "expired"})
    assert response.status_code == 401
    assert response.json()["error"] == "wechat_code_invalid"
    assert db.query(AuditLog).filter(AuditLog.action == "wechat_session_rejected").count() == 1


@pytest.mark.integration
def test_binding_conflict_is_audited_and_existing_mapping_is_preserved(wechat_client, db):
    client, service = wechat_client
    first = _member_account(db)
    second = _member_account(db)
    first_ticket = _start_binding(client, "fake:same-openid:one")
    second_ticket = _start_binding(client, "fake:same-openid:two")
    assert client.post(
        "/auth/wechat/bind",
        json={"bindingTicket": first_ticket, "username": first.username, "password": "secret123"},
    ).status_code == 200

    conflict = client.post(
        "/auth/wechat/bind",
        json={"bindingTicket": second_ticket, "username": second.username, "password": "secret123"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"] == "wechat_binding_conflict"
    identity = WechatIdentityRepository(db).get_identity_by_account(service.config.app_id, first.id)
    assert identity is not None
    assert db.query(AuditLog).filter(AuditLog.action == "wechat_binding_conflict").count() == 1


@pytest.mark.integration
def test_source_rate_limit_blocks_further_binding_attempts(wechat_client, db):
    client, service = wechat_client
    service.config = replace(service.config, binding_source_max_attempts=1)
    first_ticket = _start_binding(client, "rate-limit-1")
    first = client.post(
        "/auth/wechat/bind",
        json={"bindingTicket": first_ticket, "username": "missing", "password": "wrong"},
    )
    assert first.status_code == 401

    second_ticket = _start_binding(client, "rate-limit-2")
    second = client.post(
        "/auth/wechat/bind",
        json={"bindingTicket": second_ticket, "username": "missing", "password": "wrong"},
    )
    assert second.status_code == 429
    assert second.json()["error"] == "binding_challenge_attempts_exceeded"
    assert db.query(AuditLog).filter(AuditLog.action == "wechat_binding_ticket_abuse").count() == 1
