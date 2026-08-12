from datetime import date, datetime, timezone
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
from app.schemas.account_binding import CreateAccountBindingRequest, ResetPasswordRequest
from app.schemas.auth import ChangePasswordRequest, LoginRequest
from app.services.account_binding import AccountBindingService
from app.services.auth import AuthService
from app.services.member import MemberService


class AccountRepo:
    def __init__(self):
        self.accounts = []
        self.locked_usernames = []
        self.member_batch_queries = []

    def lock_username(self, username):
        self.locked_usernames.append(username)

    def get_by_username(self, username):
        return next((item for item in self.accounts if item.username.lower() == username.lower()), None)

    def get_by_member_id(self, member_id):
        return next((item for item in self.accounts if item.member_id == member_id), None)

    def get_by_member_ids(self, member_ids):
        self.member_batch_queries.append(member_ids)
        return [item for item in self.accounts if item.member_id in member_ids]

    def get_by_coach_profile_id(self, coach_profile_id):
        return next((item for item in self.accounts if item.coach_profile_id == coach_profile_id), None)

    def create(self, account):
        account.id = uuid4()
        account.created_at = datetime.now(timezone.utc)
        self.accounts.append(account)
        return account

    def update(self, account):
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


@pytest.mark.parametrize(
    ("role", "claim_name"),
    [("member", "memberId"), ("coach", "coachProfileId")],
)
def test_current_user_rejects_malformed_resource_claim(role, claim_name):
    token = create_access_token({"sub": f"bad-{role}", "role": role, claim_name: "not-a-uuid"})

    with pytest.raises(HTTPException) as error:
        get_current_user(
            Request({"type": "http", "method": "GET", "path": "/auth/me", "headers": []}),
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
        )

    assert error.value.status_code == 401


@pytest.mark.parametrize("resource_type", ["member", "coach"])
def test_admin_reset_replaces_hash_and_missing_account_is_404(resource_type):
    resource_id = uuid4()
    account = SimpleNamespace(
        id=uuid4(), username=f"{resource_type}-user", role=resource_type,
        member_id=resource_id if resource_type == "member" else None,
        coach_profile_id=resource_id if resource_type == "coach" else None,
        password_hash=get_password_hash("old-password"),
    )
    accounts = AccountRepo()
    accounts.accounts.append(account)
    service = AccountBindingService(accounts, ResourceRepo(), ResourceRepo())
    reset = ResetPasswordRequest(newPassword="new-password")

    if resource_type == "member":
        updated = service.reset_member_password(resource_id, reset)
        missing_call = service.reset_member_password
    else:
        updated = service.reset_coach_password(resource_id, reset)
        missing_call = service.reset_coach_password

    assert not verify_password("old-password", updated.password_hash)
    assert verify_password("new-password", updated.password_hash)
    with pytest.raises(HTTPException) as missing:
        missing_call(uuid4(), reset)
    assert missing.value.status_code == 404


def test_member_changes_password_only_after_old_password_verification():
    account = SimpleNamespace(
        id=uuid4(), username="member-user", role="member", member_id=uuid4(),
        coach_profile_id=None, password_hash=get_password_hash("old-password"),
    )
    accounts = AccountRepo()
    accounts.accounts.append(account)
    service = AuthService(accounts, ResourceRepo(), ResourceRepo())

    with pytest.raises(HTTPException) as wrong_password:
        service.change_own_password(
            account.username,
            ChangePasswordRequest(oldPassword="wrong-password", newPassword="new-password"),
        )
    assert wrong_password.value.status_code == 401
    assert verify_password("old-password", account.password_hash)

    service.change_own_password(
        account.username,
        ChangePasswordRequest(oldPassword="old-password", newPassword="new-password"),
    )
    assert not verify_password("old-password", account.password_hash)
    assert verify_password("new-password", account.password_hash)


def test_coach_changes_own_password_after_old_password_verification():
    account = SimpleNamespace(
        id=uuid4(), username="coach-user", role="coach", member_id=None,
        coach_profile_id=uuid4(), password_hash=get_password_hash("old-password"),
    )
    accounts = AccountRepo()
    accounts.accounts.append(account)
    service = AuthService(accounts, ResourceRepo(), ResourceRepo())

    with pytest.raises(HTTPException) as wrong_password:
        service.change_own_password(
            account.username,
            ChangePasswordRequest(oldPassword="wrong-password", newPassword="new-password"),
        )
    assert wrong_password.value.status_code == 401
    assert verify_password("old-password", account.password_hash)

    service.change_own_password(
        account.username,
        ChangePasswordRequest(oldPassword="old-password", newPassword="new-password"),
    )
    assert not verify_password("old-password", account.password_hash)
    assert verify_password("new-password", account.password_hash)


def test_admin_cannot_use_self_service_password_change():
    account = SimpleNamespace(
        username="admin-user", role="admin", password_hash=get_password_hash("old-password")
    )
    accounts = AccountRepo()
    accounts.accounts.append(account)

    with pytest.raises(HTTPException) as forbidden:
        AuthService(accounts, ResourceRepo(), ResourceRepo()).change_own_password(
            account.username,
            ChangePasswordRequest(oldPassword="old-password", newPassword="new-password"),
        )
    assert forbidden.value.status_code == 403
    assert verify_password("old-password", account.password_hash)


@pytest.mark.parametrize("length", [7, 129])
def test_new_password_length_boundary_is_rejected(length):
    with pytest.raises(ValueError):
        ResetPasswordRequest(newPassword="x" * length)
    with pytest.raises(ValueError):
        ChangePasswordRequest(oldPassword="old-password", newPassword="x" * length)


def test_member_list_loads_account_status_in_one_batch():
    now = datetime.now(timezone.utc)
    members = [
        SimpleNamespace(
            id=uuid4(), name=f"Member {index}", phone=f"1390000000{index}",
            gender=None, status="normal", join_date=date(2026, 8, 5), birthday=None,
            note=None, emergency_contact=None, deleted_at=None, created_at=now, updated_at=now,
        )
        for index in range(2)
    ]
    member_repo = SimpleNamespace(list=lambda *args: (members, len(members)))
    accounts = AccountRepo()
    accounts.accounts.append(
        SimpleNamespace(id=uuid4(), member_id=members[0].id, username="bound-member")
    )

    responses, total = MemberService(member_repo, accounts).list_members()

    assert total == 2
    assert accounts.member_batch_queries == [[member.id for member in members]]
    assert responses[0].has_account is True
    assert responses[0].username == "bound-member"
    assert responses[1].has_account is False
    assert responses[1].username is None
