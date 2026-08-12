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
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会员不存在")
        if member.status == "disabled":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="停用会员不能开通账号")
        if self.account_repo.get_by_member_id(member_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该会员已开通账号",
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教练不存在")
        if not coach.enabled:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="教练已停用")
        if self.account_repo.get_by_coach_profile_id(coach_profile_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该教练已开通账号",
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会员账号不存在")
        account.password_hash = get_password_hash(request.new_password)
        return self.account_repo.update(account)

    def reset_coach_password(
        self, coach_profile_id: UUID, request: ResetPasswordRequest
    ) -> AdminUser:
        account = self.account_repo.get_by_coach_profile_id(coach_profile_id)
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教练账号不存在")
        account.password_hash = get_password_hash(request.new_password)
        return self.account_repo.update(account)
