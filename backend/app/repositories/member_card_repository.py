from datetime import date
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.domain.member_card import MemberCard

class MemberCardRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, card: MemberCard) -> MemberCard:
        self.session.add(card)
        self.session.flush()
        self.session.refresh(card)
        return card

    def update(self, card: MemberCard) -> MemberCard:
        self.session.add(card)
        self.session.flush()
        self.session.refresh(card)
        return card

    def get_by_id(self, card_id: UUID, *, for_update: bool = False) -> MemberCard | None:
        stmt = select(MemberCard).where(MemberCard.id == card_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.scalars(stmt).first()

    def list_by_member(self, member_id: UUID) -> list[MemberCard]:
        return list(self.session.scalars(select(MemberCard).where(MemberCard.member_id == member_id).order_by(MemberCard.created_at.desc())).all())

    def list_fefo_candidates(
        self,
        member_id: UUID,
        today: date,
        *,
        for_update: bool = False,
        include_pending: bool = False,
        course_id: UUID | None = None,
    ) -> list[MemberCard]:
        statuses = ["active"]
        if include_pending:
            statuses.append("pending_activation")
        stmt = (
            select(MemberCard)
            .where(
                MemberCard.member_id == member_id,
                MemberCard.status.in_(statuses),
                or_(MemberCard.expires_on.is_(None), MemberCard.expires_on >= today),
                or_(MemberCard.remaining_times.is_(None), MemberCard.remaining_times > 0),
            )
            .order_by(
                case((MemberCard.status == "pending_activation", 1), else_=0),
                case((MemberCard.expires_on.is_(None), 1), else_=0),
                MemberCard.expires_on.asc(),
                MemberCard.opened_on.asc(),
                MemberCard.created_at.asc(),
            )
        )
        if for_update:
            stmt = stmt.with_for_update()
        cards = list(self.session.scalars(stmt).all())
        if course_id is None:
            return cards
        course_ref = str(course_id)
        return [
            card for card in cards
            if (card.terms_snapshot or {}).get("applicableCourseScope") == "group"
            or (
                (card.terms_snapshot or {}).get("applicableCourseScope") == "specific"
                and course_ref in ((card.terms_snapshot or {}).get("specificCourseIds") or [])
            )
        ]
