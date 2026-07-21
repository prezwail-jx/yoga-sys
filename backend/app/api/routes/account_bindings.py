from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.audit import record_audit
from app.api.deps import CurrentUser, get_account_binding_service, get_current_admin
from app.infra.db.session import get_session
from app.schemas.account_binding import AccountBindingResponse, CreateAccountBindingRequest
from app.services.account_binding import AccountBindingService
from app.services.idempotency_service import IdempotencyConflictError, IdempotencyService


router = APIRouter()


def _create_binding(
    *, resource_type: str, resource_id: UUID, payload: CreateAccountBindingRequest,
    request: Request, key: str, service: AccountBindingService,
    session: Session, user: CurrentUser,
):
    idempotency = IdempotencyService(session)
    scope = f"{resource_type}-account-create"
    request_body = {
        "resourceId": str(resource_id),
        **payload.model_dump(mode="json", by_alias=True),
    }
    request_hash = idempotency.compute_request_hash(request_body)
    idempotency.acquire(scope=scope, actor_id=user.user_id, idempotency_key=key)
    try:
        replay = idempotency.check(
            scope=scope, actor_id=user.user_id, idempotency_key=key,
            request_hash=request_hash,
        )
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if replay.hit:
        return JSONResponse(status_code=replay.response_code, content=replay.response_body)
    account = (
        service.create_member_account(resource_id, payload)
        if resource_type == "member"
        else service.create_coach_account(resource_id, payload)
    )
    body = account.model_dump(mode="json", by_alias=True)
    record_audit(
        session, trace_id=request.state.trace_id, idempotency_key=key,
        action=f"{resource_type}_account_create", user=user,
        object_type="admin_user", object_id=str(account.id), after_state=body,
    )
    idempotency.persist(
        scope=scope, actor_id=user.user_id, idempotency_key=key,
        request_hash=request_hash, response_code=201, response_body=body,
    )
    return body


@router.post(
    "/members/{memberId}/account",
    response_model=AccountBindingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_member_account(
    memberId: UUID, payload: CreateAccountBindingRequest, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    service: AccountBindingService = Depends(get_account_binding_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin),
):
    return _create_binding(
        resource_type="member", resource_id=memberId, payload=payload,
        request=request, key=idempotency_key, service=service, session=session, user=user,
    )


@router.post(
    "/coaches/{coachId}/account",
    response_model=AccountBindingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_coach_account(
    coachId: UUID, payload: CreateAccountBindingRequest, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    service: AccountBindingService = Depends(get_account_binding_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin),
):
    return _create_binding(
        resource_type="coach", resource_id=coachId, payload=payload,
        request=request, key=idempotency_key, service=service, session=session, user=user,
    )
