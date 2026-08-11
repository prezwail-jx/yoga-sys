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
from app.repositories.private_training import PrivateTrainingRepository
from app.repositories.writeoff_repository import WriteOffRepository
from app.repositories.member import MemberRepository
from app.services.auth import AuthService
from app.services.rate_limit import wechat_bind_rate_limiter
from app.services.wechat_auth import WechatAuthService
from app.services.wechat_binding_recovery import WechatBindingRecoveryService
from app.core.wechat_config import get_wechat_config
from app.integrations.wechat import FakeWechatProvider, RealWechatProvider
from app.services.card_product import CardProductService
from app.services.class_catalog import ClassCatalogService
from app.services.class_scheduling import ClassSchedulingService
from app.services.account_binding import AccountBindingService
from app.services.class_booking import ClassBookingService
from app.services.writeoff_service import WriteOffService
from app.services.member import MemberService
from app.services.private_training import PrivateTrainingService
from app.services.reporting import ReportingService


def get_admin_user_repo(session: Session = Depends(get_session)) -> AdminUserRepository:
    return AdminUserRepository(session)


def get_auth_service(repo: AdminUserRepository = Depends(get_admin_user_repo)) -> AuthService:
    return AuthService(repo)


def get_wechat_auth_service(session: Session = Depends(get_session)) -> WechatAuthService:
    config = get_wechat_config()
    provider = FakeWechatProvider(config.app_id) if config.provider == "fake" else RealWechatProvider(config)
    return WechatAuthService(
        session,
        config,
        provider,
        AuthService(AdminUserRepository(session)),
        wechat_bind_rate_limiter,
    )


def get_wechat_binding_recovery_service(
    session: Session = Depends(get_session),
) -> WechatBindingRecoveryService:
    return WechatBindingRecoveryService(session, get_wechat_config())


def get_member_repo(session: Session = Depends(get_session)) -> MemberRepository:
    return MemberRepository(session)


def get_member_service(session: Session = Depends(get_session)) -> MemberService:
    return MemberService(MemberRepository(session), AdminUserRepository(session))


def get_card_product_repo(session: Session = Depends(get_session)) -> CardProductRepository:
    return CardProductRepository(session)


def get_card_product_service(session: Session = Depends(get_session)) -> CardProductService:
    return CardProductService(CardProductRepository(session), CourseRepository(session))


def get_class_catalog_service(session: Session = Depends(get_session)) -> ClassCatalogService:
    return ClassCatalogService(
        CourseRepository(session), RoomRepository(session), CoachProfileRepository(session),
        AdminUserRepository(session),
    )


def get_class_scheduling_service(session: Session = Depends(get_session)) -> ClassSchedulingService:
    return ClassSchedulingService(
        ClassSessionRepository(session), CourseRepository(session),
        RoomRepository(session), CoachProfileRepository(session), PrivateTrainingRepository(session),
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
        session, ClassBookingRepository(session), ClassSessionRepository(session), writeoff_service,
        PrivateTrainingRepository(session),
    )


def get_private_training_service(session: Session = Depends(get_session)) -> PrivateTrainingService:
    member_repo = MemberRepository(session)
    writeoff_service = WriteOffService(
        session, member_repo, MemberCardRepository(session), WriteOffRepository(session)
    )
    return PrivateTrainingService(
        session,
        PrivateTrainingRepository(session),
        member_repo,
        CoachProfileRepository(session),
        writeoff_service,
    )


def get_reporting_service(session: Session = Depends(get_session)) -> ReportingService:
    return ReportingService(session)


get_current_admin = require_roles("admin")

__all__ = [
    "CurrentUser",
    "get_current_user",
    "get_current_admin",
    "get_auth_service",
    "get_wechat_auth_service",
    "get_wechat_binding_recovery_service",
    "get_member_service",
    "get_card_product_service",
    "get_class_catalog_service",
    "get_class_scheduling_service",
    "get_account_binding_service",
    "get_class_booking_service",
    "get_private_training_service",
    "get_reporting_service",
]
