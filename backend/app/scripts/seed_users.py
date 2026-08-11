import os

from sqlalchemy import select

from app.core.security import get_password_hash
from app.domain.admin_user import AdminUser
from app.domain.coach_profile import CoachProfile
from app.infra.db.session import unit_of_work


_PRODUCTION_DEFAULT_PASSWORDS = {"admin123", "coach123"}


def seed_user(username: str, password: str, role: str, *, overwrite: bool = False) -> None:
    with unit_of_work() as session:
        user = session.scalar(select(AdminUser).where(AdminUser.username == username))
        if user is None:
            user = AdminUser(username=username, password_hash=get_password_hash(password), role=role)
            session.add(user)
        else:
            if not overwrite:
                raise SystemExit(f"Account '{username}' already exists; refusing to modify it")
            user.password_hash = get_password_hash(password)
            user.role = role
        if role == "coach" and user.coach_profile_id is None:
            profile = CoachProfile(name=username, enabled=True)
            session.add(profile)
            session.flush()
            user.coach_profile_id = profile.id


def main() -> None:
    is_production = os.getenv("APP_ENV", "development").lower() == "production"
    if is_production:
        admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
        coach_password = os.getenv("COACH_PASSWORD", "").strip()
        if not admin_password or not coach_password:
            raise SystemExit("ADMIN_PASSWORD and COACH_PASSWORD must be set when APP_ENV=production")
        if admin_password in _PRODUCTION_DEFAULT_PASSWORDS or coach_password in _PRODUCTION_DEFAULT_PASSWORDS:
            raise SystemExit("Default seed passwords are not allowed in production")
    else:
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        coach_password = os.getenv("COACH_PASSWORD", "coach123")

    accounts = (
        (os.getenv("ADMIN_USERNAME", "admin"), admin_password, "admin"),
        (os.getenv("COACH_USERNAME", "coach"), coach_password, "coach"),
    )
    for username, password, role in accounts:
        seed_user(username, password, role, overwrite=not is_production)
    print("Seeded admin and coach accounts.")


if __name__ == "__main__":
    main()
