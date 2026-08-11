from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import jwt
import pytest

from app.core.security import ALGORITHM, SECRET_KEY, create_access_token, get_password_hash
from app.schemas.auth import LoginRequest
from app.services.auth import AuthService


class AccountRepo:
    def __init__(self):
        self.accounts: list[SimpleNamespace] = []

    def get_by_username(self, username: str):
        return next(
            (a for a in self.accounts if a.username.lower() == username.lower()),
            None,
        )


class ResourceRepo:
    def __init__(self, resource=None):
        self.resource = resource

    def get_by_id(self, resource_id, *, for_update=False):
        if self.resource and self.resource.id == resource_id:
            return self.resource
        return None


# ----------------------------------------------------------------
# 3.8  — JWT claims 参数化测试: 密码登录断言 role/memberId/coachProfileId
# ----------------------------------------------------------------

MEMBER_ID = uuid4()
COACH_PROFILE_ID = uuid4()


def _make_account(username: str, role: str, member_id=None, coach_profile_id=None):
    return SimpleNamespace(
        username=username,
        password_hash=get_password_hash("secret123"),
        role=role,
        member_id=member_id,
        coach_profile_id=coach_profile_id,
    )


class TestPasswordLoginJwtClaims:
    def test_member_gets_member_id_claim(self):
        member = SimpleNamespace(id=MEMBER_ID, status="normal")
        accounts = AccountRepo()
        accounts.accounts.append(_make_account("member1", "member", member_id=MEMBER_ID))

        svc = AuthService(accounts, ResourceRepo(member), ResourceRepo())
        resp = svc.login(LoginRequest(username="member1", password="secret123"))
        claims = jwt.decode(resp.access_token, SECRET_KEY, algorithms=[ALGORITHM])

        assert claims["sub"] == "member1"
        assert claims["role"] == "member"
        assert claims["memberId"] == str(MEMBER_ID)
        assert "coachProfileId" not in claims

    def test_coach_gets_coach_profile_id_claim(self):
        coach = SimpleNamespace(id=COACH_PROFILE_ID, enabled=True)
        accounts = AccountRepo()
        accounts.accounts.append(
            _make_account("coach1", "coach", coach_profile_id=COACH_PROFILE_ID)
        )

        svc = AuthService(accounts, ResourceRepo(), ResourceRepo(coach))
        resp = svc.login(LoginRequest(username="coach1", password="secret123"))
        claims = jwt.decode(resp.access_token, SECRET_KEY, algorithms=[ALGORITHM])

        assert claims["sub"] == "coach1"
        assert claims["role"] == "coach"
        assert claims["coachProfileId"] == str(COACH_PROFILE_ID)
        assert "memberId" not in claims

    def test_admin_has_no_resource_ids(self):
        accounts = AccountRepo()
        accounts.accounts.append(_make_account("admin1", "admin"))

        svc = AuthService(accounts, ResourceRepo(), ResourceRepo())
        resp = svc.login(LoginRequest(username="admin1", password="secret123"))
        claims = jwt.decode(resp.access_token, SECRET_KEY, algorithms=[ALGORITHM])

        assert claims["sub"] == "admin1"
        assert claims["role"] == "admin"
        assert "memberId" not in claims
        assert "coachProfileId" not in claims

    @pytest.mark.parametrize("member_status", ["normal", "paused", "expired"])
    def test_member_statuses_that_allow_login(self, member_status):
        member = SimpleNamespace(id=uuid4(), status=member_status)
        accounts = AccountRepo()
        accounts.accounts.append(_make_account("m", "member", member_id=member.id))

        svc = AuthService(accounts, ResourceRepo(member), ResourceRepo())
        resp = svc.login(LoginRequest(username="m", password="secret123"))
        claims = jwt.decode(resp.access_token, SECRET_KEY, algorithms=[ALGORITHM])
        assert claims["memberId"] == str(member.id)

    @pytest.mark.parametrize("member_status", ["disabled", None])
    def test_member_statuses_that_reject_login(self, member_status):
        member_id = uuid4()
        member = SimpleNamespace(id=member_id, status=member_status) if member_status else None
        accounts = AccountRepo()
        accounts.accounts.append(_make_account("m", "member", member_id=member_id))

        from fastapi import HTTPException

        svc = AuthService(accounts, ResourceRepo(member), ResourceRepo())
        with pytest.raises(HTTPException) as exc_info:
            svc.login(LoginRequest(username="m", password="secret123"))
        assert exc_info.value.status_code == 401

    def test_disabled_coach_rejected(self):
        coach = SimpleNamespace(id=uuid4(), enabled=False)
        accounts = AccountRepo()
        accounts.accounts.append(
            _make_account("c", "coach", coach_profile_id=coach.id)
        )

        from fastapi import HTTPException

        svc = AuthService(accounts, ResourceRepo(), ResourceRepo(coach))
        with pytest.raises(HTTPException) as exc_info:
            svc.login(LoginRequest(username="c", password="secret123"))
        assert exc_info.value.status_code == 401

    def test_token_contains_iat_and_exp(self):
        member = SimpleNamespace(id=uuid4(), status="normal")
        accounts = AccountRepo()
        accounts.accounts.append(_make_account("m", "member", member_id=member.id))

        svc = AuthService(accounts, ResourceRepo(member), ResourceRepo())
        resp = svc.login(LoginRequest(username="m", password="secret123"))
        claims = jwt.decode(resp.access_token, SECRET_KEY, algorithms=[ALGORITHM])

        assert "iat" in claims
        assert "exp" in claims
        assert claims["exp"] > claims["iat"]

    def test_incorrect_password_returns_401(self):
        accounts = AccountRepo()
        accounts.accounts.append(_make_account("m", "admin"))

        from fastapi import HTTPException

        svc = AuthService(accounts, ResourceRepo(), ResourceRepo())
        with pytest.raises(HTTPException) as exc_info:
            svc.login(LoginRequest(username="m", password="wrong"))
        assert exc_info.value.status_code == 401
