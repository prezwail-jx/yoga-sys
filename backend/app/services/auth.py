from datetime import timedelta

from fastapi import HTTPException, status

from app.core.security import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, verify_password
from app.repositories.admin_user import AdminUserRepository
from app.repositories.class_catalog import CoachProfileRepository
from app.repositories.member import MemberRepository
from app.schemas.auth import LoginRequest, LoginResponse


_LOGIN_ENABLED_MEMBER_STATUSES = {"normal", "paused", "expired"}


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
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def login(self, request: LoginRequest) -> LoginResponse:
        user = self.admin_user_repo.get_by_username(request.username)
        if not user or not verify_password(request.password, user.password_hash):
            raise self._unauthorized()

        claims: dict[str, str] = {"sub": user.username, "role": user.role}
        if user.role == "member":
            member = self.member_repo.get_by_id(user.member_id) if user.member_id else None
            if member is None or member.status not in _LOGIN_ENABLED_MEMBER_STATUSES:
                raise self._unauthorized()
            claims["memberId"] = str(member.id)
        elif user.role == "coach":
            coach = self.coach_repo.get_by_id(user.coach_profile_id) if user.coach_profile_id else None
            if coach is None or not coach.enabled:
                raise self._unauthorized()
            claims["coachProfileId"] = str(coach.id)
        elif user.role != "admin":
            raise self._unauthorized()

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data=claims, expires_delta=access_token_expires)
        return LoginResponse(access_token=access_token, role=user.role)
