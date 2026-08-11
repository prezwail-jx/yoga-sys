from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.audit import record_audit
from app.api.deps import CurrentUser, get_auth_service, get_current_user, get_wechat_auth_service
from app.infra.db.session import get_session
from app.schemas.auth import ChangePasswordRequest, CurrentUserResponse, LoginRequest, LoginResponse
from app.schemas.wechat_auth import (
    WechatAuthErrorResponse,
    WechatBindRequest,
    WechatBindResponse,
    WechatSessionRequest,
    WechatSessionResponse,
)
from app.services.auth import AuthService
from app.services.wechat_auth import WechatAuthService

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    return auth_service.login(request)


@router.post(
    "/wechat/session",
    response_model=WechatSessionResponse,
    responses={401: {"model": WechatSessionResponse}, 403: {"model": WechatSessionResponse}, 404: {"model": WechatSessionResponse}, 502: {"model": WechatSessionResponse}, 503: {"model": WechatSessionResponse}, 504: {"model": WechatSessionResponse}},
)
def wechat_session(
    payload: WechatSessionRequest,
    request: Request,
    service: WechatAuthService = Depends(get_wechat_auth_service),
):
    outcome = service.start_session(
        payload,
        client_ip=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", ""),
        trace_id=request.state.trace_id,
    )
    return JSONResponse(
        status_code=outcome.status_code,
        content=outcome.body.model_dump(by_alias=True, exclude_none=True),
    )


@router.post(
    "/wechat/bind",
    response_model=WechatBindResponse,
    responses={401: {"model": WechatAuthErrorResponse}, 404: {"model": WechatAuthErrorResponse}, 409: {"model": WechatAuthErrorResponse}, 410: {"model": WechatAuthErrorResponse}, 429: {"model": WechatAuthErrorResponse}},
)
def wechat_bind(
    payload: WechatBindRequest,
    request: Request,
    service: WechatAuthService = Depends(get_wechat_auth_service),
):
    outcome = service.bind(payload, trace_id=request.state.trace_id)
    return JSONResponse(
        status_code=outcome.status_code,
        content=outcome.body.model_dump(by_alias=True, exclude_none=True),
    )


@router.get("/me", response_model=CurrentUserResponse)
def me(user: CurrentUser = Depends(get_current_user)):
    return CurrentUserResponse(
        username=user.user_id,
        role=user.role,
        member_id=user.member_id,
        coach_profile_id=user.coach_profile_id,
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
):
    account = auth_service.change_member_password(user.user_id, payload)
    record_audit(
        session, trace_id=request.state.trace_id,
        action="member_account_password_change", user=user,
        object_type="admin_user", object_id=str(account.id), member_id=account.member_id,
        after_state={"username": account.username, "passwordUpdated": True},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
