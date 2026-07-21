from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, get_current_user, require_roles
from app.infra.db.session import get_session
from app.repositories.admin_user import AdminUserRepository
from app.repositories.card_product import CardProductRepository
from app.repositories.class_catalog import CoachProfileRepository, CourseRepository, RoomRepository
from app.repositories.class_session import ClassSessionRepository
from app.repositories.class_booking import ClassBookingRepository
from app.repositories.member_card_repository import MemberCardRepository
from app.repositories.writeoff_repository import WriteOffRepository
from app.repositories.member import MemberRepository
from app.services.auth import AuthService
from app.services.card_product import CardProductService
from app.services.class_catalog import ClassCatalogService
from app.services.class_scheduling import ClassSchedulingService
from app.services.account_binding import AccountBindingService
from app.services.class_booking import ClassBookingService
from app.services.writeoff_service import WriteOffService
from app.services.member import MemberService


def get_admin_user_repo(session: Session = Depends(get_session)) -> AdminUserRepository:
    return AdminUserRepository(session)


def get_auth_service(repo: AdminUserRepository = Depends(get_admin_user_repo)) -> AuthService:
    return AuthService(repo)


def get_member_repo(session: Session = Depends(get_session)) -> MemberRepository:
    return MemberRepository(session)


def get_member_service(repo: MemberRepository = Depends(get_member_repo)) -> MemberService:
    return MemberService(repo)


def get_card_product_repo(session: Session = Depends(get_session)) -> CardProductRepository:
    return CardProductRepository(session)


def get_card_product_service(session: Session = Depends(get_session)) -> CardProductService:
    return CardProductService(CardProductRepository(session), CourseRepository(session))


def get_class_catalog_service(session: Session = Depends(get_session)) -> ClassCatalogService:
    return ClassCatalogService(
        CourseRepository(session), RoomRepository(session), CoachProfileRepository(session)
    )


def get_class_scheduling_service(session: Session = Depends(get_session)) -> ClassSchedulingService:
    return ClassSchedulingService(
        ClassSessionRepository(session), CourseRepository(session),
        RoomRepository(session), CoachProfileRepository(session),
    )


def get_account_binding_service(session: Session = Depends(get_session)) -> AccountBindingService:
    return AccountBindingService(
        AdminUserRepository(session), MemberRepository(session), CoachProfileRepository(session)
    )


def get_class_booking_service(session: Session = Depends(get_session)) -> ClassBookingService:
    member_repo = MemberRepository(session)
    writeoff_service = WriteOffService(
        session, member_repo, MemberCardRepository(session), WriteOffRepository(session)
    )
    return ClassBookingService(
        session, ClassBookingRepository(session), ClassSessionRepository(session), writeoff_service
    )


get_current_admin = require_roles("admin")

__all__ = [
    "CurrentUser",
    "get_current_user",
    "get_current_admin",
    "get_auth_service",
    "get_member_service",
    "get_card_product_service",
    "get_class_catalog_service",
    "get_class_scheduling_service",
    "get_account_binding_service",
    "get_class_booking_service",
]
