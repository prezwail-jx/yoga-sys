from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_admin
from app.api.deps.business_clock import get_business_today
from app.infra.db.session import get_session
from app.infra.observability import business_span
from app.repositories.member import MemberRepository
from app.repositories.member_card_repository import MemberCardRepository
from app.repositories.writeoff_repository import WriteOffRepository
from app.schemas.writeoff import CreateWriteOffEventRequest, WriteOffEventResponse
from app.services.idempotency_service import IdempotencyConflictError, IdempotencyService
from app.services.writeoff_service import WriteOffService

router = APIRouter()

@router.post("/writeoff/events", response_model=WriteOffEventResponse)
def create_writeoff_event(
    payload: CreateWriteOffEventRequest,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_admin),
    today=Depends(get_business_today),
):
    idempotency = IdempotencyService(session)
    request_body = payload.model_dump(mode="json", exclude_none=True)
    request_hash = idempotency.compute_request_hash(request_body)
    idempotency.acquire(scope="writeoff-events", actor_id=user.user_id, idempotency_key=idempotency_key)
    try:
        replay = idempotency.check(scope="writeoff-events", actor_id=user.user_id, idempotency_key=idempotency_key, request_hash=request_hash)
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if replay.hit:
        return JSONResponse(status_code=replay.response_code, content=replay.response_body)
    service = WriteOffService(session, MemberRepository(session), MemberCardRepository(session), WriteOffRepository(session))
    with business_span("writeoff.apply", business_action=payload.event_type, member_id=payload.member_id, actor_role=user.role):
        event = service.apply(
            member_id=payload.member_id, business_ref=payload.business_ref, event_type=payload.event_type,
            user=user, idempotency_key=idempotency_key, trace_id=request.state.trace_id, today=today,
        )
    body = WriteOffEventResponse.model_validate(event).model_dump(mode="json", by_alias=True)
    idempotency.persist(
        scope="writeoff-events", actor_id=user.user_id, idempotency_key=idempotency_key,
        request_hash=request_hash, response_code=200, response_body=body,
    )
    return body
