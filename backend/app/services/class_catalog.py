from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status

from app.domain.coach_profile import CoachProfile
from app.domain.course import Course
from app.domain.room import Room
from app.repositories.class_catalog import CoachProfileRepository, CourseRepository, RoomRepository
from app.schemas.class_catalog import (
    CreateCoachRequest,
    CreateCourseRequest,
    CreateRoomRequest,
    UpdateCoachRequest,
    UpdateCourseRequest,
    UpdateRoomRequest,
)


class ClassCatalogService:
    def __init__(
        self,
        course_repo: CourseRepository,
        room_repo: RoomRepository,
        coach_repo: CoachProfileRepository,
    ):
        self.course_repo = course_repo
        self.room_repo = room_repo
        self.coach_repo = coach_repo

    @staticmethod
    def _not_found(kind: str) -> HTTPException:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{kind} not found")

    @staticmethod
    def _normalized_name(name: str) -> str:
        normalized = name.strip()
        if not normalized:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Name must not be blank")
        return normalized

    def _ensure_unique_name(self, repo, name: str, exclude_id: UUID | None = None) -> str:
        normalized = self._normalized_name(name)
        repo.lock_name(normalized)
        if repo.name_exists(normalized, exclude_id=exclude_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Name already exists")
        return normalized

    def _validate_specialties(self, course_ids: list[UUID] | None) -> list[str] | None:
        if course_ids is None:
            return None
        unique_ids = set(course_ids)
        missing = unique_ids - self.course_repo.existing_ids(unique_ids)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Specialty course not found: {sorted(str(item) for item in missing)[0]}",
            )
        return [str(item) for item in dict.fromkeys(course_ids)]

    def create_course(self, request: CreateCourseRequest) -> Course:
        values = request.model_dump(mode="json")
        values["name"] = self._ensure_unique_name(self.course_repo, request.name)
        if values.get("cover_url") is not None:
            values["cover_url"] = str(values["cover_url"])
        return self.course_repo.create(Course(**values))

    def get_course(self, course_id: UUID) -> Course:
        course = self.course_repo.get_by_id(course_id)
        if course is None:
            raise self._not_found("Course")
        return course

    def list_courses(self, **filters):
        return self.course_repo.list(**filters)

    def update_course(self, course_id: UUID, request: UpdateCourseRequest) -> Course:
        course = self.get_course(course_id)
        changes = request.model_dump(mode="json", exclude_unset=True)
        if "name" in changes:
            changes["name"] = self._ensure_unique_name(self.course_repo, changes["name"], course_id)
        if changes.get("cover_url") is not None:
            changes["cover_url"] = str(changes["cover_url"])
        for field, value in changes.items():
            setattr(course, field, value)
        return self.course_repo.update(course)

    def create_room(self, request: CreateRoomRequest) -> Room:
        values = request.model_dump()
        values["name"] = self._ensure_unique_name(self.room_repo, request.name)
        return self.room_repo.create(Room(**values))

    def get_room(self, room_id: UUID) -> Room:
        room = self.room_repo.get_by_id(room_id)
        if room is None:
            raise self._not_found("Room")
        return room

    def list_rooms(self, **filters):
        return self.room_repo.list(**filters)

    def update_room(self, room_id: UUID, request: UpdateRoomRequest) -> Room:
        room = self.get_room(room_id)
        changes = request.model_dump(exclude_unset=True)
        if "name" in changes:
            changes["name"] = self._ensure_unique_name(self.room_repo, changes["name"], room_id)
        if "capacity" in changes and changes["capacity"] < room.capacity:
            minimum = self.room_repo.max_future_session_capacity(room_id, datetime.now(timezone.utc))
            if changes["capacity"] < minimum:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Room capacity cannot be lower than future session capacity {minimum}",
                )
        for field, value in changes.items():
            setattr(room, field, value)
        return self.room_repo.update(room)

    def create_coach(self, request: CreateCoachRequest) -> CoachProfile:
        values = request.model_dump(mode="json")
        values["name"] = self._ensure_unique_name(self.coach_repo, request.name)
        values["specialty_course_ids"] = self._validate_specialties(request.specialty_course_ids)
        if values.get("avatar_url") is not None:
            values["avatar_url"] = str(values["avatar_url"])
        return self.coach_repo.create(CoachProfile(**values))

    def get_coach(self, coach_id: UUID) -> CoachProfile:
        coach = self.coach_repo.get_by_id(coach_id)
        if coach is None:
            raise self._not_found("Coach")
        return coach

    def list_coaches(self, **filters):
        return self.coach_repo.list(**filters)

    def update_coach(self, coach_id: UUID, request: UpdateCoachRequest) -> CoachProfile:
        coach = self.get_coach(coach_id)
        changes = request.model_dump(mode="json", exclude_unset=True)
        if "name" in changes:
            changes["name"] = self._ensure_unique_name(self.coach_repo, changes["name"], coach_id)
        if "specialty_course_ids" in changes:
            changes["specialty_course_ids"] = self._validate_specialties(request.specialty_course_ids)
        if changes.get("avatar_url") is not None:
            changes["avatar_url"] = str(changes["avatar_url"])
        for field, value in changes.items():
            setattr(coach, field, value)
        return self.coach_repo.update(coach)
