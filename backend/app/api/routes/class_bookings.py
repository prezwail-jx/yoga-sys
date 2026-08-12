from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_class_booking_service, get_current_user
from app.api.deps.business_clock import get_business_now, get_business_today
from app.infra.db.session import get_session
from app.schemas.class_booking import (
    CancelClassBookingRequest,
    ClassBookingListResponse,
    ClassBookingResponse,
    CreateClassBookingRequest,
)
from app.services.class_booking import ClassBookingService
from app.services.idempotency_service import IdempotencyConflictError, IdempotencyService


router = APIRouter()


def _body(value: dict, actor: CurrentUser) -> dict:
    body = ClassBookingResponse.model_validate(value).model_dump(mode="json", by_alias=True)
    if actor.role == "member":
        for field in ("bookedById", "bookedByRole", "terminalById", "terminalByRole"):
            body[field] = None
    return body


def _idempotency_replay(
    session: Session, *, scope: str, actor_id: str, key: str, payload: dict,
):
    service = IdempotencyService(session)
    request_hash = service.compute_request_hash(payload)
    service.acquire(scope=scope, actor_id=actor_id, idempotency_key=key)
    try:
        replay = service.check(
            scope=scope, actor_id=actor_id, idempotency_key=key,
            request_hash=request_hash,
        )
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return service, request_hash, replay


@router.get("/class-sessions/{sessionId}/bookings", response_model=ClassBookingListResponse)
def list_session_bookings(
    sessionId: UUID,
    service: ClassBookingService = Depends(get_class_booking_service),
    user: CurrentUser = Depends(get_current_user),
):
    service.assert_session_roster_readable(sessionId, user)
    items = [_body(item, user) for item in service.list_session(sessionId)]
    return {"items": items, "total": len(items), "skip": 0, "limit": len(items) or 1}


@router.post(
    "/class-sessions/{sessionId}/bookings",
    response_model=ClassBookingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_booking(
    sessionId: UUID, payload: CreateClassBookingRequest, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    service: ClassBookingService = Depends(get_class_booking_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user),
    now: datetime = Depends(get_business_now), today: date = Depends(get_business_today),
):
    request_body = {"sessionId": str(sessionId), **payload.model_dump(mode="json", by_alias=True)}
    idem, request_hash, replay = _idempotency_replay(
        session, scope="class-booking-create", actor_id=user.user_id,
        key=idempotency_key, payload=request_body,
    )
    if replay.hit:
        return JSONResponse(status_code=replay.response_code, content=replay.response_body)
    value = service.create(
        session_id=sessionId, member_id=payload.member_id, actor=user,
        idempotency_key=idempotency_key, trace_id=request.state.trace_id,
        now=now, today=today,
    )
    body = _body(value, user)
    idem.persist(
        scope="class-booking-create", actor_id=user.user_id,
        idempotency_key=idempotency_key, request_hash=request_hash,
        response_code=201, response_body=body,
    )
    return body


@router.post("/class-bookings/{bookingId}/cancel", response_model=ClassBookingResponse)
def cancel_booking(
    bookingId: UUID, request: Request, payload: CancelClassBookingRequest | None = None,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    service: ClassBookingService = Depends(get_class_booking_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user),
    now: datetime = Depends(get_business_now), today: date = Depends(get_business_today),
):
    reason = payload.reason if payload else None
    request_body = {"bookingId": str(bookingId), "action": "cancel", "reason": reason}
    idem, request_hash, replay = _idempotency_replay(
        session, scope="class-booking-cancel", actor_id=user.user_id,
        key=idempotency_key, payload=request_body,
    )
    if replay.hit:
        return JSONResponse(status_code=replay.response_code, content=replay.response_body)
    value = service.cancel(
        bookingId, actor=user, idempotency_key=idempotency_key,
        trace_id=request.state.trace_id, reason=reason, now=now, today=today,
    )
    body = _body(value, user)
    idem.persist(
        scope="class-booking-cancel", actor_id=user.user_id,
        idempotency_key=idempotency_key, request_hash=request_hash,
        response_code=200, response_body=body,
    )
    return body


@router.post("/class-bookings/{bookingId}/check-in", response_model=ClassBookingResponse)
def check_in_booking(
    bookingId: UUID, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    service: ClassBookingService = Depends(get_class_booking_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user),
    now: datetime = Depends(get_business_now), today: date = Depends(get_business_today),
):
    request_body = {"bookingId": str(bookingId), "action": "check-in"}
    idem, request_hash, replay = _idempotency_replay(
        session, scope="class-booking-check-in", actor_id=user.user_id,
        key=idempotency_key, payload=request_body,
    )
    if replay.hit:
        return JSONResponse(status_code=replay.response_code, content=replay.response_body)
    value = service.check_in(
        bookingId, actor=user, idempotency_key=idempotency_key,
        trace_id=request.state.trace_id, now=now, today=today,
    )
    body = _body(value, user)
    idem.persist(
        scope="class-booking-check-in", actor_id=user.user_id,
        idempotency_key=idempotency_key, request_hash=request_hash,
        response_code=200, response_body=body,
    )
    return body


@router.get("/members/me/bookings", response_model=ClassBookingListResponse)
def list_my_bookings(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    service: ClassBookingService = Depends(get_class_booking_service),
    user: CurrentUser = Depends(get_current_user),
):
    if user.role != "member":
        raise HTTPException(status_code=403, detail="需要会员身份")
    items, total = service.list_member(actor=user, skip=skip, limit=limit)
    return {
        "items": [_body(item, user) for item in items],
        "total": total, "skip": skip, "limit": limit,
    }
