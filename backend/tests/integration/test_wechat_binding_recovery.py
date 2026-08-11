from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_wechat_auth_service, get_wechat_binding_recovery_service
from app.infra.db.session import get_session
from app.core.security import get_password_hash
from app.core.wechat_config import WechatConfig
from app.domain.admin_user import AdminUser
from app.domain.audit_log import AuditLog
from app.domain.coach_profile import CoachProfile
from app.domain.member import Member
from app.integrations.wechat import FakeWechatProvider
from app.main import app
from app.repositories.admin_user import AdminUserRepository
from app.services.auth import AuthService
from app.services.rate_limit import SlidingWindowRateLimiter
from app.services.wechat_auth import WechatAuthService
from app.services.wechat_binding_recovery import WechatBindingRecoveryService


@pytest.fixture
def recovery_client(db):
    config = WechatConfig.for_tests(app_id=f"wx-recovery-{uuid4().hex[:12]}", identity_pepper="r" * 32)
    auth_service = WechatAuthService(
        db,
        config,
        FakeWechatProvider(config.app_id),
        AuthService(AdminUserRepository(db)),
        SlidingWindowRateLimiter(),
    )
    recovery_service = WechatBindingRecoveryService(db, config)

    def override_get_session():
        transaction = db.begin_nested()
        try:
            yield db
            if transaction.is_active:
                transaction.commit()
        except Exception:
            if transaction.is_active:
                transaction.rollback()
            raise

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_wechat_auth_service] = lambda: auth_service
    app.dependency_overrides[get_wechat_binding_recovery_service] = lambda: recovery_service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _member_account(db) -> AdminUser:
    suffix = uuid4().hex[:12]
    member = Member(
        name=f"Recovery Member {suffix}",
        phone=f"13{uuid4().int % 1_000_000_000:09d}",
        join_date=date(2026, 8, 6),
        status="normal",
    )
    db.add(member)
    db.flush()
    account = AdminUser(
        username=f"recovery-member-{suffix}",
        password_hash=get_password_hash("secret123"),
        role="member",
        member_id=member.id,
    )
    db.add(account)
    db.flush()
    return account


def _coach_account(db) -> AdminUser:
    suffix = uuid4().hex[:12]
    coach = CoachProfile(name=f"Recovery Coach {suffix}", enabled=True)
    db.add(coach)
    db.flush()
    account = AdminUser(
        username=f"recovery-coach-{suffix}",
        password_hash=get_password_hash("secret123"),
        role="coach",
        coach_profile_id=coach.id,
    )
    db.add(account)
    db.flush()
    return account


def _bind(client: TestClient, account: AdminUser, identity: str) -> None:
    session = client.post("/auth/wechat/session", json={"code": f"fake:{identity}:one"})
    assert session.status_code == 200
    ticket = session.json()["bindingTicket"]
    bound = client.post(
        "/auth/wechat/bind",
        json={"bindingTicket": ticket, "username": account.username, "password": "secret123"},
    )
    assert bound.status_code == 200


def _admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.integration
def test_admin_can_query_member_and_coach_binding_status_without_identity_material(recovery_client, db):
    member_account = _member_account(db)
    coach_account = _coach_account(db)
    _bind(recovery_client, member_account, "member-status")
    auth_headers = _admin_headers(recovery_client)

    bound = recovery_client.get(
        f"/accounts/{member_account.id}/wechat-binding", headers=auth_headers
    )
    unbound = recovery_client.get(
        f"/accounts/{coach_account.id}/wechat-binding", headers=auth_headers
    )

    assert bound.status_code == 200
    assert bound.json()["accountId"] == str(member_account.id)
    assert bound.json()["bound"] is True
    assert bound.json()["boundAt"]
    assert "openid" not in bound.text.lower()
    assert unbound.status_code == 200
    assert unbound.json() == {"accountId": str(coach_account.id), "bound": False, "boundAt": None}


@pytest.mark.integration
def test_admin_unbinds_member_and_standard_rebinding_is_allowed(recovery_client, db):
    account = _member_account(db)
    _bind(recovery_client, account, "member-rebind")
    auth_headers = _admin_headers(recovery_client)

    response = recovery_client.request(
        "DELETE",
        f"/accounts/{account.id}/wechat-binding",
        json={"confirm": True},
        headers=auth_headers,
    )
    assert response.status_code == 204

    status = recovery_client.get(f"/accounts/{account.id}/wechat-binding", headers=auth_headers)
    assert status.json()["bound"] is False
    audit = db.query(AuditLog).filter(AuditLog.action == "wechat_binding_unbind").one()
    assert audit.operator_id == "admin"
    assert audit.operator_role == "admin"
    assert audit.object_id == str(account.id)
    assert audit.after_state == {"role": "member", "wechatBound": False}
    assert "openid" not in str(audit.after_state).lower()

    session = recovery_client.post("/auth/wechat/session", json={"code": "fake:member-rebind:two"})
    assert session.status_code == 200
    assert session.json()["state"] == "binding_required"
    rebound = recovery_client.post(
        "/auth/wechat/bind",
        json={
            "bindingTicket": session.json()["bindingTicket"],
            "username": account.username,
            "password": "secret123",
        },
    )
    assert rebound.status_code == 200


@pytest.mark.integration
def test_admin_unbinds_coach_and_unbound_account_returns_explicit_conflict(recovery_client, db):
    account = _coach_account(db)
    auth_headers = _admin_headers(recovery_client)
    not_bound = recovery_client.request(
        "DELETE",
        f"/accounts/{account.id}/wechat-binding",
        json={"confirm": True},
        headers=auth_headers,
    )
    assert not_bound.status_code == 409
    assert not_bound.json()["detail"] == "wechat_binding_not_found"
    assert db.query(AuditLog).filter(AuditLog.action == "wechat_binding_unbind").count() == 0

    _bind(recovery_client, account, "coach-unbind")
    response = recovery_client.request(
        "DELETE",
        f"/accounts/{account.id}/wechat-binding",
        json={"confirm": True},
        headers=auth_headers,
    )
    assert response.status_code == 204
    assert db.query(AuditLog).filter(AuditLog.action == "wechat_binding_unbind").one().after_state == {
        "role": "coach",
        "wechatBound": False,
    }


@pytest.mark.integration
def test_non_admin_cannot_unbind_and_rejection_is_audited(recovery_client, db):
    account = _member_account(db)
    _bind(recovery_client, account, "member-forbidden")
    auth_headers = _admin_headers(recovery_client)
    login = recovery_client.post(
        "/auth/login", json={"username": account.username, "password": "secret123"}
    )
    member_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    forbidden = recovery_client.request(
        "DELETE",
        f"/accounts/{account.id}/wechat-binding",
        json={"confirm": True},
        headers=member_headers,
    )
    assert forbidden.status_code == 403
    assert recovery_client.get(
        f"/accounts/{account.id}/wechat-binding", headers=auth_headers
    ).json()["bound"] is True
    rejected = db.query(AuditLog).filter(
        AuditLog.action == "delete_accounts",
        AuditLog.object_id == str(account.id),
    ).one()
    assert rejected.result == "rejected"
    assert rejected.operator_id == account.username


@pytest.mark.integration
def test_unbind_requires_explicit_true_confirmation(recovery_client, db):
    account = _member_account(db)
    _bind(recovery_client, account, "confirmation")
    auth_headers = _admin_headers(recovery_client)

    response = recovery_client.request(
        "DELETE",
        f"/accounts/{account.id}/wechat-binding",
        json={"confirm": False},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert recovery_client.get(
        f"/accounts/{account.id}/wechat-binding", headers=auth_headers
    ).json()["bound"] is True
