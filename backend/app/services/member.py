from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.domain.member import Member
from app.repositories.member import MemberRepository
from app.repositories.admin_user import AdminUserRepository
from app.repositories.member_card_repository import MemberCardRepository
from app.schemas.member import CreateMemberRequest, MemberCardSummary, MemberResponse, UpdateMemberRequest

_ALLOWED_TRANSITIONS = {
    "normal": {"normal", "paused", "disabled"},
    "paused": {"paused", "normal", "disabled"},
    "disabled": {"disabled", "normal"},
    "expired": {"expired"},
}


class MemberService:
    def __init__(
        self,
        member_repo: MemberRepository,
        account_repo: AdminUserRepository | None = None,
        member_card_repo: MemberCardRepository | None = None,
    ):
        self.member_repo = member_repo
        self.account_repo = account_repo
        self.member_card_repo = member_card_repo

    def create_member(self, req: CreateMemberRequest) -> Member:
        if self.member_repo.get_by_phone(req.phone):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="手机号已被注册")
        member = Member(**req.model_dump(), status="normal")
        try:
            return self.member_repo.create(member)
        except IntegrityError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="手机号已被注册") from exc

    def get_member(self, member_id: UUID) -> Member:
        member = self.member_repo.get_by_id(member_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会员不存在")
        return member

    def list_members(
        self,
        skip: int = 0,
        limit: int = 20,
        keyword: str | None = None,
        member_status: str | None = None,
        today: date | None = None,
    ) -> tuple[list[MemberResponse], int]:
        members, total = self.member_repo.list(skip, limit, keyword, member_status)
        accounts = (
            self.account_repo.get_by_member_ids([member.id for member in members])
            if self.account_repo
            else []
        )
        accounts_by_member = {account.member_id: account for account in accounts}
        cards_by_member = self._cards_by_member([member.id for member in members], today)
        return [self._response(member, accounts_by_member.get(member.id), cards_by_member.get(member.id, [])) for member in members], total

    def get_member_response(self, member_id: UUID, today: date | None = None) -> MemberResponse:
        member = self.get_member(member_id)
        account = self.account_repo.get_by_member_id(member_id) if self.account_repo else None
        cards = self._cards_by_member([member_id], today).get(member_id, [])
        return self._response(member, account, cards)

    def _cards_by_member(self, member_ids: list[UUID], today: date | None = None) -> dict[UUID, list[MemberCardSummary]]:
        result: dict[UUID, list[MemberCardSummary]] = {}
        if not self.member_card_repo:
            return result
        for card in self.member_card_repo.list_by_member_ids(member_ids):
            status = card.status
            expires_on = card.expires_on
            if today and status == "frozen" and card.frozen_until and card.frozen_from and today >= card.frozen_until:
                expires_on = expires_on + timedelta(days=max(1, (card.frozen_until - card.frozen_from).days)) if expires_on else None
                status = "active"
            if today and status == "active" and expires_on and today > expires_on:
                status = "expired"
            summary = MemberCardSummary.model_validate(card).model_copy(
                update={"status": status, "expires_on": expires_on}
            )
            result.setdefault(card.member_id, []).append(summary)
        return result

    @staticmethod
    def _response(member: Member, account=None, cards=None) -> MemberResponse:
        return MemberResponse.model_validate(member).model_copy(
            update={
                "has_account": account is not None,
                "username": account.username if account is not None else None,
                "account_id": account.id if account is not None else None,
                "card_summaries": cards or [],
            }
        )

    def update_member(self, member_id: UUID, req: UpdateMemberRequest) -> Member:
        member = self.get_member(member_id)
        changes = req.model_dump(exclude_unset=True)
        next_status = changes.get("status")
        if next_status and next_status not in _ALLOWED_TRANSITIONS[member.status]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"无效的会员状态变更：{member.status} -> {next_status}",
            )
        for field, value in changes.items():
            setattr(member, field, value)
        return self.member_repo.update(member)

    def delete_member(self, member_id: UUID) -> Member:
        member = self.get_member(member_id)
        member.deleted_at = datetime.now(timezone.utc)
        return self.member_repo.update(member)

    def ensure_bookable(self, member_id: UUID) -> Member:
        member = self.get_member(member_id)
        if member.status != "normal":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"会员状态 {member.status} 不允许预约",
            )
        return member
