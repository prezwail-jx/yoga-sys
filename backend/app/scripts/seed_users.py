import os

from sqlalchemy import select

from app.core.security import get_password_hash
from app.domain.admin_user import AdminUser
from app.domain.coach_profile import CoachProfile
from app.infra.db.session import unit_of_work


def seed_user(username: str, password: str, role: str) -> None:
    with unit_of_work() as session:
        user = session.scalar(select(AdminUser).where(AdminUser.username == username))
        if user is None:
            session.add(AdminUser(username=username, password_hash=get_password_hash(password), role=role))
        else:
            user.password_hash = get_password_hash(password)
            user.role = role
        if role == "coach" and user.coach_profile_id is None:
            profile = CoachProfile(name=username, enabled=True)
            session.add(profile)
            session.flush()
            user.coach_profile_id = profile.id


def main() -> None:
    accounts = (
        (os.getenv("ADMIN_USERNAME", "admin"), os.getenv("ADMIN_PASSWORD", "admin123"), "admin"),
        (os.getenv("COACH_USERNAME", "coach"), os.getenv("COACH_PASSWORD", "coach123"), "coach"),
    )
    for username, password, role in accounts:
        seed_user(username, password, role)
    print("Seeded admin and coach accounts.")


if __name__ == "__main__":
    main()
