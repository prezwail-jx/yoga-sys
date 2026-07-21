from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from app.api.deps.auth import CurrentUser, get_current_user
from app.api.endpoints.auth import me
from app.core.security import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.schemas.account_binding import CreateAccountBindingRequest
from app.schemas.auth import LoginRequest
from app.services.account_binding import AccountBindingService
from app.services.auth import AuthService


class AccountRepo:
    def __init__(self):
        self.accounts = []
        self.locked_usernames = []

    def lock_username(self, username):
        self.locked_usernames.append(username)

    def get_by_username(self, username):
        return next((item for item in self.accounts if item.username.lower() == username.lower()), None)

    def get_by_member_id(self, member_id):
        return next((item for item in self.accounts if item.member_id == member_id), None)

    def get_by_coach_profile_id(self, coach_profile_id):
        return next((item for item in self.accounts if item.coach_profile_id == coach_profile_id), None)

    def create(self, account):
        account.id = uuid4()
        account.created_at = datetime.now(timezone.utc)
        self.accounts.append(account)
        return account


class ResourceRepo:
    def __init__(self, resource=None):
        self.resource = resource
        self.for_update = False

    def get_by_id(self, resource_id, *, for_update=False):
        self.for_update = for_update
        if self.resource is not None and self.resource.id == resource_id:
            return self.resource
        return None


def test_member_binding_normalizes_username_hashes_password_and_locks_resource():
    member = SimpleNamespace(id=uuid4(), status="normal")
    accounts = AccountRepo()
    members = ResourceRepo(member)
    service = AccountBindingService(accounts, members, ResourceRepo())

    response = service.create_member_account(
        member.id,
        CreateAccountBindingRequest(username="  Alice.Member  ", initialPassword="secret123"),
    )

    assert response.username == "alice.member"
    assert response.member_id == member.id
    assert response.coach_profile_id is None
    assert accounts.locked_usernames == ["alice.member"]
    assert members.for_update is True
    assert verify_password("secret123", accounts.accounts[0].password_hash)
    assert "password" not in response.model_dump_json()


def test_binding_rejects_duplicate_resource_and_disabled_coach():
    member = SimpleNamespace(id=uuid4(), status="normal")
    coach = SimpleNamespace(id=uuid4(), enabled=False)
    accounts = AccountRepo()
    accounts.accounts.append(
        SimpleNamespace(member_id=member.id, coach_profile_id=None, username="existing")
    )
    service = AccountBindingService(accounts, ResourceRepo(member), ResourceRepo(coach))

    with pytest.raises(HTTPException) as duplicate:
        service.create_member_account(
            member.id,
            CreateAccountBindingRequest(username="new-member", initialPassword="secret123"),
        )
    assert duplicate.value.status_code == 409

    with pytest.raises(HTTPException) as disabled:
        service.create_coach_account(
            coach.id,
            CreateAccountBindingRequest(username="new-coach", initialPassword="secret123"),
        )
    assert disabled.value.status_code == 409


def test_coach_binding_is_unique_and_returns_no_password_fields():
    coach = SimpleNamespace(id=uuid4(), enabled=True)
    accounts = AccountRepo()
    coaches = ResourceRepo(coach)
    service = AccountBindingService(accounts, ResourceRepo(), coaches)

    response = service.create_coach_account(
        coach.id,
        CreateAccountBindingRequest(username=" Coach.One ", initialPassword="secret123"),
    )

    assert response.username == "coach.one"
    assert response.coach_profile_id == coach.id
    assert response.member_id is None
    assert coaches.for_update is True
    assert "password" not in response.model_dump_json()

    with pytest.raises(HTTPException) as duplicate_username:
        service.create_member_account(
            uuid4(),
            CreateAccountBindingRequest(username="COACH.ONE", initialPassword="secret123"),
        )
    assert duplicate_username.value.status_code == 409


@pytest.mark.parametrize("member_status", ["normal", "paused", "expired"])
def test_member_login_issues_resource_scoped_token(member_status):
    member = SimpleNamespace(id=uuid4(), status=member_status)
    user = SimpleNamespace(
        username="member-user",
        password_hash=get_password_hash("secret123"),
        role="member",
        member_id=member.id,
        coach_profile_id=None,
    )
    accounts = AccountRepo()
    accounts.accounts.append(user)

    response = AuthService(accounts, ResourceRepo(member), ResourceRepo()).login(
        LoginRequest(username=" MEMBER-USER ", password="secret123")
    )
    claims = jwt.decode(response.access_token, SECRET_KEY, algorithms=[ALGORITHM])

    assert claims["memberId"] == str(member.id)
    assert "coachProfileId" not in claims


@pytest.mark.parametrize("member_status", ["disabled", None])
def test_member_login_rejects_disabled_or_deleted_resource(member_status):
    member_id = uuid4()
    member = SimpleNamespace(id=member_id, status=member_status) if member_status else None
    user = SimpleNamespace(
        username="member-user",
        password_hash=get_password_hash("secret123"),
        role="member",
        member_id=member_id,
        coach_profile_id=None,
    )
    accounts = AccountRepo()
    accounts.accounts.append(user)

    with pytest.raises(HTTPException) as error:
        AuthService(accounts, ResourceRepo(member), ResourceRepo()).login(
            LoginRequest(username="member-user", password="secret123")
        )
    assert error.value.status_code == 401


def test_coach_requires_enabled_binding_but_unbound_admin_remains_compatible():
    coach_id = uuid4()
    coach = SimpleNamespace(id=coach_id, enabled=True)
    accounts = AccountRepo()
    coach_user = SimpleNamespace(
        username="coach-user",
        password_hash=get_password_hash("secret123"),
        role="coach",
        member_id=None,
        coach_profile_id=coach_id,
    )
    accounts.accounts.append(coach_user)
    service = AuthService(accounts, ResourceRepo(), ResourceRepo(coach))

    response = service.login(LoginRequest(username="coach-user", password="secret123"))
    claims = jwt.decode(response.access_token, SECRET_KEY, algorithms=[ALGORITHM])
    assert claims["coachProfileId"] == str(coach_id)

    coach_user.coach_profile_id = None
    with pytest.raises(HTTPException) as unbound_coach:
        service.login(LoginRequest(username="coach-user", password="secret123"))
    assert unbound_coach.value.status_code == 401

    accounts.accounts[0] = SimpleNamespace(
        username="admin",
        password_hash=get_password_hash("admin123"),
        role="admin",
        member_id=None,
        coach_profile_id=None,
    )
    assert service.login(LoginRequest(username="admin", password="admin123")).role == "admin"


def test_disabled_coach_cannot_login():
    coach = SimpleNamespace(id=uuid4(), enabled=False)
    user = SimpleNamespace(
        username="coach-user",
        password_hash=get_password_hash("secret123"),
        role="coach",
        member_id=None,
        coach_profile_id=coach.id,
    )
    accounts = AccountRepo()
    accounts.accounts.append(user)

    with pytest.raises(HTTPException) as error:
        AuthService(accounts, ResourceRepo(), ResourceRepo(coach)).login(
            LoginRequest(username="coach-user", password="secret123")
        )
    assert error.value.status_code == 401


def test_current_user_and_me_expose_coach_profile_id():
    coach_id = uuid4()
    token = create_access_token(
        {"sub": "coach-user", "role": "coach", "coachProfileId": str(coach_id)}
    )
    user = get_current_user(
        Request({"type": "http", "method": "GET", "path": "/auth/me", "headers": []}),
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
    )

    assert user == CurrentUser(
        user_id="coach-user",
        role="coach",
        coach_profile_id=str(coach_id),
    )
    assert me(user).model_dump(by_alias=True)["coachProfileId"] == str(coach_id)


def test_current_user_rejects_unbound_coach_token():
    token = create_access_token({"sub": "legacy-coach", "role": "coach"})

    with pytest.raises(HTTPException) as error:
        get_current_user(
            Request({"type": "http", "method": "GET", "path": "/auth/me", "headers": []}),
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
        )
    assert error.value.status_code == 401
