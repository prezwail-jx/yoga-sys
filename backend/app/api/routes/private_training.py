from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_private_training_service
from app.api.deps.business_clock import get_business_now, get_business_today
from app.infra.db.session import get_session
from app.schemas.private_training import (
    PrivateAvailabilityInput,
    PrivateAvailabilityList,
    PrivateAvailabilityResponse,
    PrivateAvailabilityWeekInput,
    PrivateAvailabilityWeekResult,
    PrivateBookingDecisionInput,
    PrivateBookingInput,
    PrivateBookingList,
    PrivateBookingResponse,
    PrivateLessonRecordInput,
)
from app.services.idempotency_service import IdempotencyConflictError, IdempotencyService
from app.services.private_training import PrivateTrainingService


router = APIRouter()


def _replay(session: Session, *, scope: str, actor_id: str, key: str, payload: dict):
    service = IdempotencyService(session)
    request_hash = service.compute_request_hash(payload)
    service.acquire(scope=scope, actor_id=actor_id, idempotency_key=key)
    try:
        replay = service.check(scope=scope, actor_id=actor_id, idempotency_key=key, request_hash=request_hash)
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return service, request_hash, replay


def _slot_body(value: dict) -> dict:
    return PrivateAvailabilityResponse.model_validate(value).model_dump(mode="json", by_alias=True)


def _booking_body(value: dict) -> dict:
    return PrivateBookingResponse.model_validate(value).model_dump(mode="json", by_alias=True)


def _slot_mutation(
    session: Session,
    *,
    scope: str,
    actor_id: str,
    key: str | None,
    payload: dict,
    response_code: int,
    mutate: Callable[[], dict],
):
    if key is None:
        return mutate()
    idem, request_hash, replay = _replay(
        session, scope=scope, actor_id=actor_id, key=key, payload=payload,
    )
    if replay.hit:
        return JSONResponse(status_code=replay.response_code, content=replay.response_body)
    body = _slot_body(mutate())
    idem.persist(
        scope=scope,
        actor_id=actor_id,
        idempotency_key=key,
        request_hash=request_hash,
        response_code=response_code,
        response_body=body,
    )
    return body


@router.get("/private-slots", response_model=PrivateAvailabilityList)
def list_private_slots(
    date_from: datetime | None = Query(None, alias="dateFrom"),
    date_to: datetime | None = Query(None, alias="dateTo"),
    coach_id: UUID | None = Query(None, alias="coachId"),
    service: PrivateTrainingService = Depends(get_private_training_service),
    user: CurrentUser = Depends(get_current_user),
):
    items, total = service.list_slots(actor=user, date_from=date_from, date_to=date_to, coach_id=coach_id)
    return {"items": [_slot_body(item) for item in items], "total": total}


@router.post("/private-slots", response_model=PrivateAvailabilityResponse, status_code=status.HTTP_201_CREATED)
def create_private_slot(
    payload: PrivateAvailabilityInput, request: Request,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", min_length=8, max_length=128),
    service: PrivateTrainingService = Depends(get_private_training_service),
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
    now=Depends(get_business_now),
):
    body_in = payload.model_dump(mode="json", by_alias=True)
    return _slot_mutation(
        session,
        scope="private-slot-create",
        actor_id=user.user_id,
        key=idempotency_key,
        payload=body_in,
        response_code=201,
        mutate=lambda: service.create_slot(
            payload, actor=user, trace_id=request.state.trace_id, now=now,
        ),
    )


@router.post("/private-slots/generate-week", response_model=PrivateAvailabilityWeekResult)
def generate_private_week(
    payload: PrivateAvailabilityWeekInput, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    service: PrivateTrainingService = Depends(get_private_training_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user),
    now=Depends(get_business_now),
):
    idem, request_hash, replay = _replay(
        session, scope="private-slot-generate-week", actor_id=user.user_id,
        key=idempotency_key, payload=payload.model_dump(mode="json", by_alias=True),
    )
    if replay.hit:
        return JSONResponse(status_code=replay.response_code, content=replay.response_body)
    created, conflicts = service.generate_week(
        payload, actor=user, trace_id=request.state.trace_id, now=now,
    )
    body = PrivateAvailabilityWeekResult(created=created, conflicts=conflicts).model_dump(mode="json", by_alias=True)
    idem.persist(scope="private-slot-generate-week", actor_id=user.user_id, idempotency_key=idempotency_key, request_hash=request_hash, response_code=200, response_body=body)
    return body


@router.patch("/private-slots/{slotId}", response_model=PrivateAvailabilityResponse)
def update_private_slot(
    slotId: UUID, payload: PrivateAvailabilityInput, request: Request,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", min_length=8, max_length=128),
    service: PrivateTrainingService = Depends(get_private_training_service),
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
    now=Depends(get_business_now),
):
    body_in = {"slotId": str(slotId), **payload.model_dump(mode="json", by_alias=True)}
    return _slot_mutation(
        session,
        scope="private-slot-update",
        actor_id=user.user_id,
        key=idempotency_key,
        payload=body_in,
        response_code=200,
        mutate=lambda: service.update_slot(
            slotId, payload, actor=user, trace_id=request.state.trace_id, now=now,
        ),
    )


@router.delete("/private-slots/{slotId}", response_model=PrivateAvailabilityResponse)
def cancel_private_slot(
    slotId: UUID, request: Request,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", min_length=8, max_length=128),
    service: PrivateTrainingService = Depends(get_private_training_service),
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
):
    return _slot_mutation(
        session,
        scope="private-slot-cancel",
        actor_id=user.user_id,
        key=idempotency_key,
        payload={"slotId": str(slotId)},
        response_code=200,
        mutate=lambda: service.cancel_slot(
            slotId, actor=user, trace_id=request.state.trace_id,
        ),
    )


@router.get("/private-bookings", response_model=PrivateBookingList)
def list_private_bookings(
    status_filter: str | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    service: PrivateTrainingService = Depends(get_private_training_service),
    user: CurrentUser = Depends(get_current_user),
):
    items, total = service.list_bookings(actor=user, status=status_filter, skip=skip, limit=limit)
    return {"items": [_booking_body(item) for item in items], "total": total, "skip": skip, "limit": limit}


@router.post("/private-bookings", response_model=PrivateBookingResponse, status_code=status.HTTP_201_CREATED)
def create_private_booking(
    payload: PrivateBookingInput, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    service: PrivateTrainingService = Depends(get_private_training_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user),
    now=Depends(get_business_now),
):
    body_in = payload.model_dump(mode="json", by_alias=True)
    idem, request_hash, replay = _replay(session, scope="private-booking-create", actor_id=user.user_id, key=idempotency_key, payload=body_in)
    if replay.hit:
        return JSONResponse(status_code=replay.response_code, content=replay.response_body)
    value = service.create_booking(payload, actor=user, trace_id=request.state.trace_id, now=now)
    body = _booking_body(value)
    idem.persist(scope="private-booking-create", actor_id=user.user_id, idempotency_key=idempotency_key, request_hash=request_hash, response_code=201, response_body=body)
    return body


@router.get("/private-bookings/{bookingId}", response_model=PrivateBookingResponse)
def get_private_booking(
    bookingId: UUID,
    service: PrivateTrainingService = Depends(get_private_training_service),
    user: CurrentUser = Depends(get_current_user),
):
    return service.get_booking(bookingId, actor=user)


def _booking_action(
    *, booking_id: UUID, action: str, payload: dict, request: Request,
    key: str, service: PrivateTrainingService, session: Session, user: CurrentUser, now, today,
):
    idem, request_hash, replay = _replay(session, scope=f"private-booking-{action}", actor_id=user.user_id, key=key, payload=payload)
    if replay.hit:
        return JSONResponse(status_code=replay.response_code, content=replay.response_body)
    if action == "confirm":
        value = service.confirm_booking(booking_id, actor=user, idempotency_key=key, trace_id=request.state.trace_id, now=now, today=today)
    elif action == "reject":
        value = service.reject_booking(booking_id, actor=user, reason=payload.get("reason"), trace_id=request.state.trace_id, now=now)
    elif action == "cancel":
        value = service.cancel_pending_booking(booking_id, actor=user, reason=payload.get("reason"), trace_id=request.state.trace_id, now=now)
    else:
        raise HTTPException(status_code=422, detail="不支持的私教预约操作")
    body = _booking_body(value)
    idem.persist(scope=f"private-booking-{action}", actor_id=user.user_id, idempotency_key=key, request_hash=request_hash, response_code=200, response_body=body)
    return body


@router.post("/private-bookings/{bookingId}/confirm", response_model=PrivateBookingResponse)
def confirm_private_booking(
    bookingId: UUID, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    service: PrivateTrainingService = Depends(get_private_training_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user),
    now=Depends(get_business_now), today=Depends(get_business_today),
):
    return _booking_action(booking_id=bookingId, action="confirm", payload={"bookingId": str(bookingId)}, request=request, key=idempotency_key, service=service, session=session, user=user, now=now, today=today)


@router.post("/private-bookings/{bookingId}/reject", response_model=PrivateBookingResponse)
def reject_private_booking(
    bookingId: UUID, payload: PrivateBookingDecisionInput | None, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    service: PrivateTrainingService = Depends(get_private_training_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user),
    now=Depends(get_business_now), today=Depends(get_business_today),
):
    reason = payload.reason if payload else None
    return _booking_action(booking_id=bookingId, action="reject", payload={"bookingId": str(bookingId), "reason": reason}, request=request, key=idempotency_key, service=service, session=session, user=user, now=now, today=today)


@router.post("/private-bookings/{bookingId}/cancel", response_model=PrivateBookingResponse)
def cancel_private_booking(
    bookingId: UUID, payload: PrivateBookingDecisionInput | None, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    service: PrivateTrainingService = Depends(get_private_training_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user),
    now=Depends(get_business_now), today=Depends(get_business_today),
):
    reason = payload.reason if payload else None
    return _booking_action(booking_id=bookingId, action="cancel", payload={"bookingId": str(bookingId), "reason": reason}, request=request, key=idempotency_key, service=service, session=session, user=user, now=now, today=today)


@router.post("/private-bookings/{bookingId}/sign-in", response_model=PrivateBookingResponse)
def sign_in_private_booking(
    bookingId: UUID, payload: PrivateLessonRecordInput, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    service: PrivateTrainingService = Depends(get_private_training_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_user),
    now=Depends(get_business_now), today=Depends(get_business_today),
):
    idem, request_hash, replay = _replay(session, scope="private-booking-sign-in", actor_id=user.user_id, key=idempotency_key, payload={"bookingId": str(bookingId), **payload.model_dump(mode="json", by_alias=True)})
    if replay.hit:
        return JSONResponse(status_code=replay.response_code, content=replay.response_body)
    value = service.sign_in_booking(bookingId, payload, actor=user, idempotency_key=idempotency_key, trace_id=request.state.trace_id, now=now, today=today)
    body = _booking_body(value)
    idem.persist(scope="private-booking-sign-in", actor_id=user.user_id, idempotency_key=idempotency_key, request_hash=request_hash, response_code=200, response_body=body)
    return body
