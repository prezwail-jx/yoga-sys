from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.domain.member import Member
from app.repositories.member import MemberRepository
from app.schemas.member import CreateMemberRequest, UpdateMemberRequest

_ALLOWED_TRANSITIONS = {
    "normal": {"normal", "paused", "disabled"},
    "paused": {"paused", "normal", "disabled"},
    "disabled": {"disabled"},
    "expired": {"expired"},
}


class MemberService:
    def __init__(self, member_repo: MemberRepository):
        self.member_repo = member_repo

    def create_member(self, req: CreateMemberRequest) -> Member:
        if self.member_repo.get_by_phone(req.phone):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone number already registered")
        member = Member(**req.model_dump(), status="normal")
        try:
            return self.member_repo.create(member)
        except IntegrityError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone number already registered") from exc

    def get_member(self, member_id: UUID) -> Member:
        member = self.member_repo.get_by_id(member_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
        return member

    def list_members(
        self,
        skip: int = 0,
        limit: int = 20,
        keyword: str | None = None,
        member_status: str | None = None,
    ) -> tuple[list[Member], int]:
        return self.member_repo.list(skip, limit, keyword, member_status)

    def update_member(self, member_id: UUID, req: UpdateMemberRequest) -> Member:
        member = self.get_member(member_id)
        changes = req.model_dump(exclude_unset=True)
        next_status = changes.get("status")
        if next_status and next_status not in _ALLOWED_TRANSITIONS[member.status]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Invalid member status transition: {member.status} -> {next_status}",
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
                detail=f"Member status {member.status} does not allow booking",
            )
        return member
