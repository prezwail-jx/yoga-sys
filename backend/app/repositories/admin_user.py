from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.domain.admin_user import AdminUser


class AdminUserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_username(self, username: str) -> AdminUser | None:
        stmt = select(AdminUser).where(func.lower(AdminUser.username) == username.strip().lower())
        return self.session.scalars(stmt).first()

    def lock_username(self, username: str) -> None:
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"admin_user:username:{username.strip().lower()}"},
        )

    def get_by_member_id(self, member_id: UUID) -> AdminUser | None:
        return self.session.scalars(
            select(AdminUser).where(AdminUser.member_id == member_id)
        ).first()

    def get_by_coach_profile_id(self, coach_profile_id: UUID) -> AdminUser | None:
        return self.session.scalars(
            select(AdminUser).where(AdminUser.coach_profile_id == coach_profile_id)
        ).first()

    def create(self, user: AdminUser) -> AdminUser:
        self.session.add(user)
        self.session.flush()
        self.session.refresh(user)
        return user
