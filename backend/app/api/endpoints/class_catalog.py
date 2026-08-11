from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.audit import record_audit
from app.api.deps import CurrentUser, get_class_catalog_service, get_current_admin, get_current_user
from app.infra.db.session import get_session
from app.schemas.class_catalog import (
    CoachListResponse,
    CoachResponse,
    CourseListResponse,
    CourseResponse,
    CreateCoachRequest,
    CreateCourseRequest,
    CreateRoomRequest,
    RoomListResponse,
    RoomResponse,
    UpdateCoachRequest,
    UpdateCourseRequest,
    UpdateRoomRequest,
)
from app.services.class_catalog import ClassCatalogService


router = APIRouter()


def _state(item, model) -> dict:
    return model.model_validate(item).model_dump(mode="json", by_alias=True)


def _audit(session, request, user, action, object_type, item, model, before=None) -> None:
    record_audit(
        session, trace_id=request.state.trace_id, action=action, user=user,
        object_type=object_type, object_id=str(item.id), before_state=before,
        after_state=_state(item, model),
    )


@router.get("/courses", response_model=CourseListResponse)
def list_courses(
    keyword: str | None = Query(None, max_length=100), enabled: bool | None = None,
    skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
    service: ClassCatalogService = Depends(get_class_catalog_service),
    _: CurrentUser = Depends(get_current_user),
):
    items, total = service.list_courses(skip=skip, limit=limit, keyword=keyword, enabled=enabled)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CreateCourseRequest, request: Request,
    service: ClassCatalogService = Depends(get_class_catalog_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin),
):
    item = service.create_course(payload)
    _audit(session, request, user, "course_create", "course", item, CourseResponse)
    return item


@router.get("/courses/{courseId}", response_model=CourseResponse)
def get_course(
    courseId: UUID, service: ClassCatalogService = Depends(get_class_catalog_service),
    _: CurrentUser = Depends(get_current_user),
):
    return service.get_course(courseId)


@router.patch("/courses/{courseId}", response_model=CourseResponse)
def update_course(
    courseId: UUID, payload: UpdateCourseRequest, request: Request,
    service: ClassCatalogService = Depends(get_class_catalog_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin),
):
    before = _state(service.get_course(courseId), CourseResponse)
    item = service.update_course(courseId, payload)
    _audit(session, request, user, "course_update", "course", item, CourseResponse, before)
    return item


@router.get("/rooms", response_model=RoomListResponse)
def list_rooms(
    keyword: str | None = Query(None, max_length=100), enabled: bool | None = None,
    skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
    service: ClassCatalogService = Depends(get_class_catalog_service),
    _: CurrentUser = Depends(get_current_user),
):
    items, total = service.list_rooms(skip=skip, limit=limit, keyword=keyword, enabled=enabled)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(
    payload: CreateRoomRequest, request: Request,
    service: ClassCatalogService = Depends(get_class_catalog_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin),
):
    item = service.create_room(payload)
    _audit(session, request, user, "room_create", "room", item, RoomResponse)
    return item


@router.get("/rooms/{roomId}", response_model=RoomResponse)
def get_room(
    roomId: UUID, service: ClassCatalogService = Depends(get_class_catalog_service),
    _: CurrentUser = Depends(get_current_user),
):
    return service.get_room(roomId)


@router.patch("/rooms/{roomId}", response_model=RoomResponse)
def update_room(
    roomId: UUID, payload: UpdateRoomRequest, request: Request,
    service: ClassCatalogService = Depends(get_class_catalog_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin),
):
    before = _state(service.get_room(roomId), RoomResponse)
    item = service.update_room(roomId, payload)
    _audit(session, request, user, "room_update", "room", item, RoomResponse, before)
    return item


@router.get("/coaches", response_model=CoachListResponse)
def list_coaches(
    keyword: str | None = Query(None, max_length=100), enabled: bool | None = None,
    skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
    service: ClassCatalogService = Depends(get_class_catalog_service),
    _: CurrentUser = Depends(get_current_user),
):
    items, total = service.list_coaches(skip=skip, limit=limit, keyword=keyword, enabled=enabled)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/coaches", response_model=CoachResponse, status_code=status.HTTP_201_CREATED)
def create_coach(
    payload: CreateCoachRequest, request: Request,
    service: ClassCatalogService = Depends(get_class_catalog_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin),
):
    item = service.create_coach(payload)
    _audit(session, request, user, "coach_create", "coach_profile", item, CoachResponse)
    return item


@router.get("/coaches/{coachId}", response_model=CoachResponse)
def get_coach(
    coachId: UUID, service: ClassCatalogService = Depends(get_class_catalog_service),
    _: CurrentUser = Depends(get_current_user),
):
    return service.get_coach_response(coachId)


@router.patch("/coaches/{coachId}", response_model=CoachResponse)
def update_coach(
    coachId: UUID, payload: UpdateCoachRequest, request: Request,
    service: ClassCatalogService = Depends(get_class_catalog_service),
    session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin),
):
    before = _state(service.get_coach(coachId), CoachResponse)
    item = service.update_coach(coachId, payload)
    _audit(session, request, user, "coach_update", "coach_profile", item, CoachResponse, before)
    return item
