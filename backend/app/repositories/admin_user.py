from sqlalchemy.orm import Session
from sqlalchemy import select
from app.domain.admin_user import AdminUser

class AdminUserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_username(self, username: str) -> AdminUser | None:
        stmt = select(AdminUser).where(AdminUser.username == username)
        return self.session.scalars(stmt).first()
