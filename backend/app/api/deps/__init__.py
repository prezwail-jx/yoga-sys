from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser, get_current_user, require_roles
from app.infra.db.session import get_session
from app.repositories.admin_user import AdminUserRepository
from app.repositories.card_product import CardProductRepository
from app.repositories.member import MemberRepository
from app.services.auth import AuthService
from app.services.card_product import CardProductService
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


def get_card_product_service(repo: CardProductRepository = Depends(get_card_product_repo)) -> CardProductService:
    return CardProductService(repo)


get_current_admin = require_roles("admin")

__all__ = [
    "CurrentUser",
    "get_current_user",
    "get_current_admin",
    "get_auth_service",
    "get_member_service",
    "get_card_product_service",
]
