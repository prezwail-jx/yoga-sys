from datetime import timedelta

from fastapi import HTTPException, status

from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.repositories.admin_user import AdminUserRepository
from app.repositories.class_catalog import CoachProfileRepository
from app.repositories.member import MemberRepository
from app.schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse


_LOGIN_ENABLED_MEMBER_STATUSES = {"normal", "paused", "expired"}


class AccountIneligibleError(ValueError):
    pass


class AuthService:
    def __init__(
        self,
        admin_user_repo: AdminUserRepository,
        member_repo: MemberRepository | None = None,
        coach_repo: CoachProfileRepository | None = None,
    ):
        self.admin_user_repo = admin_user_repo
        self.member_repo = member_repo or MemberRepository(admin_user_repo.session)
        self.coach_repo = coach_repo or CoachProfileRepository(admin_user_repo.session)

    @staticmethod
    def _unauthorized() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def login(self, request: LoginRequest) -> LoginResponse:
        user = self.authenticate_credentials(request.username, request.password)
        if user is None:
            raise self._unauthorized()

        try:
            return self.issue_token_for_account(user)
        except AccountIneligibleError:
            raise self._unauthorized()

    def authenticate_credentials(self, username: str, password: str):
        user = self.admin_user_repo.get_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            return None
        return user

    def issue_token_for_account(self, user) -> LoginResponse:
        claims = self.build_claims(user)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data=claims, expires_delta=access_token_expires)
        return LoginResponse(access_token=access_token, role=user.role)

    def build_claims(self, user) -> dict[str, str]:
        claims: dict[str, str] = {"sub": user.username, "role": user.role}
        if user.role == "member":
            member = self.member_repo.get_by_id(user.member_id) if user.member_id else None
            if member is None or member.status not in _LOGIN_ENABLED_MEMBER_STATUSES:
                raise AccountIneligibleError("member account is not login eligible")
            claims["memberId"] = str(member.id)
        elif user.role == "coach":
            coach = self.coach_repo.get_by_id(user.coach_profile_id) if user.coach_profile_id else None
            if coach is None or not coach.enabled:
                raise AccountIneligibleError("coach account is not login eligible")
            claims["coachProfileId"] = str(coach.id)
        elif user.role != "admin":
            raise AccountIneligibleError("unknown account role")
        return claims

    def change_own_password(self, username: str, request: ChangePasswordRequest):
        user = self.admin_user_repo.get_by_username(username)
        if user is None or user.role not in {"admin", "member", "coach"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有权限")
        if not verify_password(request.old_password, user.password_hash):
            raise self._unauthorized()
        user.password_hash = get_password_hash(request.new_password)
        return self.admin_user_repo.update(user)
