from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_auth_service, get_current_user
from app.schemas.auth import CurrentUserResponse, LoginRequest, LoginResponse
from app.services.auth import AuthService

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    return auth_service.login(request)


@router.get("/me", response_model=CurrentUserResponse)
def me(user: CurrentUser = Depends(get_current_user)):
    return CurrentUserResponse(username=user.user_id, role=user.role, member_id=user.member_id)
