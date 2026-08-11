from uuid import UUID

from fastapi import HTTPException, status

from app.core.security import get_password_hash
from app.domain.admin_user import AdminUser
from app.repositories.admin_user import AdminUserRepository
from app.repositories.class_catalog import CoachProfileRepository
from app.repositories.member import MemberRepository
from app.schemas.account_binding import (
    AccountBindingResponse,
    CreateAccountBindingRequest,
    ResetPasswordRequest,
)


class AccountBindingService:
    def __init__(
        self,
        account_repo: AdminUserRepository,
        member_repo: MemberRepository,
        coach_repo: CoachProfileRepository,
    ):
        self.account_repo = account_repo
        self.member_repo = member_repo
        self.coach_repo = coach_repo

    def _prepare_username(self, username: str) -> str:
        normalized = username.strip().lower()
        self.account_repo.lock_username(normalized)
        if self.account_repo.get_by_username(normalized) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
        return normalized

    @staticmethod
    def _response(account: AdminUser) -> AccountBindingResponse:
        return AccountBindingResponse.model_validate(account)

    def create_member_account(
        self,
        member_id: UUID,
        request: CreateAccountBindingRequest,
    ) -> AccountBindingResponse:
        username = self._prepare_username(request.username)
        member = self.member_repo.get_by_id(member_id, for_update=True)
        if member is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
        if member.status == "disabled":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Disabled member cannot have an account")
        if self.account_repo.get_by_member_id(member_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Member already has an account",
            )
        account = AdminUser(
            username=username,
            password_hash=get_password_hash(request.initial_password),
            role="member",
            member_id=member.id,
        )
        return self._response(self.account_repo.create(account))

    def create_coach_account(
        self,
        coach_profile_id: UUID,
        request: CreateAccountBindingRequest,
    ) -> AccountBindingResponse:
        username = self._prepare_username(request.username)
        coach = self.coach_repo.get_by_id(coach_profile_id, for_update=True)
        if coach is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coach not found")
        if not coach.enabled:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Coach is disabled")
        if self.account_repo.get_by_coach_profile_id(coach_profile_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Coach already has an account",
            )
        account = AdminUser(
            username=username,
            password_hash=get_password_hash(request.initial_password),
            role="coach",
            coach_profile_id=coach.id,
        )
        return self._response(self.account_repo.create(account))

    def reset_member_password(self, member_id: UUID, request: ResetPasswordRequest) -> AdminUser:
        account = self.account_repo.get_by_member_id(member_id)
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member account not found")
        account.password_hash = get_password_hash(request.new_password)
        return self.account_repo.update(account)

    def reset_coach_password(
        self, coach_profile_id: UUID, request: ResetPasswordRequest
    ) -> AdminUser:
        account = self.account_repo.get_by_coach_profile_id(coach_profile_id)
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coach account not found")
        account.password_hash = get_password_hash(request.new_password)
        return self.account_repo.update(account)
