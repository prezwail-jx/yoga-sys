from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domain.member import Member


class MemberRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, member_id: UUID) -> Member | None:
        stmt = select(Member).where(Member.id == member_id, Member.deleted_at.is_(None))
        return self.session.scalars(stmt).first()

    def get_by_phone(self, phone: str, include_deleted: bool = True) -> Member | None:
        stmt = select(Member).where(Member.phone == phone)
        if not include_deleted:
            stmt = stmt.where(Member.deleted_at.is_(None))
        return self.session.scalars(stmt).first()

    def create(self, member: Member) -> Member:
        self.session.add(member)
        self.session.flush()
        self.session.refresh(member)
        return member

    def list(
        self,
        skip: int = 0,
        limit: int = 20,
        keyword: str | None = None,
        member_status: str | None = None,
    ) -> tuple[list[Member], int]:
        filters = [Member.deleted_at.is_(None)]
        if keyword:
            filters.append(or_(Member.name.ilike(f"%{keyword}%"), Member.phone.ilike(f"%{keyword}%")))
        if member_status:
            filters.append(Member.status == member_status)
        items = list(
            self.session.scalars(
                select(Member)
                .where(*filters)
                .order_by(Member.created_at.desc())
                .offset(skip)
                .limit(limit)
            ).all()
        )
        total = self.session.scalar(select(func.count()).select_from(Member).where(*filters)) or 0
        return items, total

    def update(self, member: Member) -> Member:
        self.session.add(member)
        self.session.flush()
        self.session.refresh(member)
        return member
