from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.audit import record_audit
from app.api.deps import (
    CurrentUser, get_class_booking_service, get_class_scheduling_service,
    get_current_admin, get_current_user,
)
from app.api.deps.business_clock import get_business_now, get_business_today
from app.infra.db.session import get_session
from app.schemas.class_scheduling import (
    ClassSessionListResponse,
    ClassSessionResponse,
    CopyWeekRequest,
    CopyWeekResponse,
    CreateClassSessionRequest,
    UpdateClassSessionRequest,
)
from app.services.class_scheduling import ClassSchedulingService
from app.services.class_booking import ClassBookingService
from app.services.idempotency_service import IdempotencyConflictError, IdempotencyService


router = APIRouter(prefix="/class-sessions")


def _body(value: dict) -> dict:
    return ClassSessionResponse.model_validate(value).model_dump(mode="json", by_alias=True)


def _audit(session, request, user, action, value, before=None, key=None) -> None:
    record_audit(
        session, trace_id=request.state.trace_id, idempotency_key=key,
        action=action, user=user, object_type="class_session",
        object_id=str(value["id"]), before_state=before, after_state=_body(value),
    )


def _replay_or_none(idempotency, *, scope, actor_id, key, request_hash):
    idempotency.acquire(scope=scope, actor_id=actor_id, idempotency_key=key)
    try:
        replay = idempotency.check(
            scope=scope, actor_id=actor_id, idempotency_key=key, request_hash=request_hash
        )
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if replay.hit:
        return JSONResponse(status_code=replay.response_code, content=replay.response_body)
    return None


@router.get("", response_model=ClassSessionListResponse)
def list_class_sessions(
    week_start: date = Query(..., alias="weekStart"),
    service: ClassSchedulingService = Depends(get_class_scheduling_service),
    user: CurrentUser = Depends(get_current_user),
):
    coach_profile_id = UUID(user.coach_profile_id) if user.role == "coach" and user.coach_profile_id else None
    items, week_end = service.list_week(
        week_start,
        include_drafts=user.role == "admin",
        coach_profile_id=coach_profile_id,
    )
    return {"items": items, "week_start": week_start, "week_end": week_end}


@router.post("", response_model=ClassSessionResponse, status_code=status.HTTP_201_CREATED)
def create_class_session(
    payload: CreateClassSessionRequest, request: Request,
    service: ClassSchedulingService = Depends(get_class_scheduling_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin),
):
    value = service.create(payload, user.user_id)
    _audit(session, request, user, "class_session_create", value)
    return value


@router.post("/copy-week", response_model=CopyWeekResponse)
def copy_week(
    payload: CopyWeekRequest, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    service: ClassSchedulingService = Depends(get_class_scheduling_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin),
):
    idempotency = IdempotencyService(session)
    request_body = payload.model_dump(mode="json")
    request_hash = idempotency.compute_request_hash(request_body)
    replay = _replay_or_none(
        idempotency, scope="class-session-copy-week", actor_id=user.user_id,
        key=idempotency_key, request_hash=request_hash,
    )
    if replay:
        return replay
    created, conflicts = service.copy_week(
        payload.source_week_start, payload.target_week_start, user.user_id
    )
    body = CopyWeekResponse(created=created, conflicts=conflicts).model_dump(mode="json", by_alias=True)
    record_audit(
        session, trace_id=request.state.trace_id, idempotency_key=idempotency_key,
        action="class_session_copy_week", user=user, object_type="class_session_week",
        object_id=payload.target_week_start.isoformat(),
        after_state={"createdIds": [item["id"] for item in body["created"]], "conflicts": body["conflicts"]},
    )
    idempotency.persist(
        scope="class-session-copy-week", actor_id=user.user_id,
        idempotency_key=idempotency_key, request_hash=request_hash,
        response_code=200, response_body=body,
    )
    return body


@router.get("/{sessionId}", response_model=ClassSessionResponse)
def get_class_session(
    sessionId: UUID, service: ClassSchedulingService = Depends(get_class_scheduling_service),
    _: CurrentUser = Depends(get_current_user),
):
    return service.get(sessionId)


@router.patch("/{sessionId}", response_model=ClassSessionResponse)
def update_class_session(
    sessionId: UUID, payload: UpdateClassSessionRequest, request: Request,
    service: ClassSchedulingService = Depends(get_class_scheduling_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin),
):
    before = _body(service.get(sessionId))
    value = service.update(sessionId, payload)
    _audit(session, request, user, "class_session_update", value, before)
    return value


def _transition(
    session_id: UUID, action: str, request: Request, service: ClassSchedulingService,
    session: Session, user: CurrentUser, idempotency_key: str | None = None,
):
    before = _body(service.get(session_id))
    if idempotency_key is None:
        value = service.transition(session_id, action)
        _audit(session, request, user, f"class_session_{action}", value, before)
        return value
    idempotency = IdempotencyService(session)
    scope = f"class-session-{action}"
    request_hash = idempotency.compute_request_hash({"sessionId": str(session_id), "action": action})
    replay = _replay_or_none(
        idempotency, scope=scope, actor_id=user.user_id,
        key=idempotency_key, request_hash=request_hash,
    )
    if replay:
        return replay
    value = service.transition(session_id, action)
    body = _body(value)
    _audit(session, request, user, f"class_session_{action}", value, before, idempotency_key)
    idempotency.persist(
        scope=scope, actor_id=user.user_id, idempotency_key=idempotency_key,
        request_hash=request_hash, response_code=200, response_body=body,
    )
    return body


@router.post("/{sessionId}/publish", response_model=ClassSessionResponse)
def publish_class_session(
    sessionId: UUID, request: Request,
    service: ClassSchedulingService = Depends(get_class_scheduling_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin),
):
    return _transition(sessionId, "publish", request, service, session, user)


@router.post("/{sessionId}/pause", response_model=ClassSessionResponse)
def pause_class_session(
    sessionId: UUID, request: Request,
    service: ClassSchedulingService = Depends(get_class_scheduling_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin),
):
    return _transition(sessionId, "pause", request, service, session, user)


@router.post("/{sessionId}/resume", response_model=ClassSessionResponse)
def resume_class_session(
    sessionId: UUID, request: Request,
    service: ClassSchedulingService = Depends(get_class_scheduling_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin),
):
    return _transition(sessionId, "resume", request, service, session, user)


@router.post("/{sessionId}/cancel", response_model=ClassSessionResponse)
def cancel_class_session(
    sessionId: UUID, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    booking_service: ClassBookingService = Depends(get_class_booking_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin),
    now=Depends(get_business_now), today=Depends(get_business_today),
):
    idempotency = IdempotencyService(session)
    scope = "class-session-cancel"
    request_hash = idempotency.compute_request_hash({"sessionId": str(sessionId), "action": "cancel"})
    replay = _replay_or_none(
        idempotency, scope=scope, actor_id=user.user_id,
        key=idempotency_key, request_hash=request_hash,
    )
    if replay:
        return replay
    value = booking_service.cancel_session(
        sessionId, actor=user, idempotency_key=idempotency_key,
        trace_id=request.state.trace_id, reason="venue_cancel", now=now, today=today,
    )
    body = _body(value)
    idempotency.persist(
        scope=scope, actor_id=user.user_id, idempotency_key=idempotency_key,
        request_hash=request_hash, response_code=200, response_body=body,
    )
    return body


@router.post("/{sessionId}/complete", response_model=ClassSessionResponse)
def complete_class_session(
    sessionId: UUID, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    booking_service: ClassBookingService = Depends(get_class_booking_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin),
    now=Depends(get_business_now), today=Depends(get_business_today),
):
    idempotency = IdempotencyService(session)
    scope = "class-session-complete"
    request_hash = idempotency.compute_request_hash({"sessionId": str(sessionId), "action": "complete"})
    replay = _replay_or_none(
        idempotency, scope=scope, actor_id=user.user_id,
        key=idempotency_key, request_hash=request_hash,
    )
    if replay:
        return replay
    value = booking_service.complete_session(
        sessionId, actor=user, idempotency_key=idempotency_key,
        trace_id=request.state.trace_id, now=now, today=today,
    )
    body = _body(value)
    idempotency.persist(
        scope=scope, actor_id=user.user_id, idempotency_key=idempotency_key,
        request_hash=request_hash, response_code=200, response_body=body,
    )
    return body
