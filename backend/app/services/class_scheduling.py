from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from app.domain.class_session import ClassSession
from app.repositories.class_catalog import CoachProfileRepository, CourseRepository, RoomRepository
from app.repositories.class_session import ClassSessionRepository
from app.repositories.private_training import PrivateTrainingRepository
from app.schemas.class_scheduling import CreateClassSessionRequest, UpdateClassSessionRequest


SHANGHAI = ZoneInfo("Asia/Shanghai")
KEY_FIELDS = {"course_id", "coach_profile_id", "room_id", "start_at", "end_at"}
TRANSITIONS = {
    "publish": ({"draft"}, "published"),
    "pause": ({"published"}, "paused"),
    "resume": ({"paused"}, "published"),
    "cancel": ({"draft", "published", "paused"}, "cancelled"),
    "complete": ({"published", "paused"}, "completed"),
}


class ClassSchedulingService:
    def __init__(
        self,
        session_repo: ClassSessionRepository,
        course_repo: CourseRepository,
        room_repo: RoomRepository,
        coach_repo: CoachProfileRepository,
        private_repo: PrivateTrainingRepository | None = None,
    ):
        self.session_repo = session_repo
        self.course_repo = course_repo
        self.room_repo = room_repo
        self.coach_repo = coach_repo
        self.private_repo = private_repo

    @staticmethod
    def _week_bounds(week_start: date) -> tuple[datetime, datetime]:
        if week_start.weekday() != 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="weekStart 必须是周一")
        local_start = datetime.combine(week_start, time.min, SHANGHAI)
        return local_start.astimezone(timezone.utc), (local_start + timedelta(days=7)).astimezone(timezone.utc)

    @staticmethod
    def _aware(value: datetime, field: str) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"{field} 必须包含时区")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _missing(kind: str) -> HTTPException:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到{kind}")

    def _resources(
        self,
        course_id: UUID,
        coach_id: UUID,
        room_id: UUID,
        capacity: int,
    ):
        # All scheduling writes use the same lock order to serialize conflict checks.
        coach = self.coach_repo.get_by_id(coach_id, for_update=True)
        room = self.room_repo.get_by_id(room_id, for_update=True)
        course = self.course_repo.get_by_id(course_id)
        for resource, kind in ((course, "Course"), (coach, "Coach"), (room, "Room")):
            if resource is None:
                raise self._missing(kind)
            if not resource.enabled:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{kind} 已停用")
        if capacity > room.capacity:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="课次容量超过教室容量")
        return course, coach, room

    def _validate_schedule(
        self,
        *,
        course_id: UUID,
        coach_id: UUID,
        room_id: UUID,
        start_at: datetime,
        end_at: datetime,
        capacity: int,
        exclude_id: UUID | None = None,
    ) -> None:
        if end_at <= start_at:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="endAt 必须晚于 startAt")
        self._resources(course_id, coach_id, room_id, capacity)
        reason = self.session_repo.conflict_reason(
            coach_id=coach_id,
            room_id=room_id,
            start_at=start_at,
            end_at=end_at,
            exclude_id=exclude_id,
        )
        if reason:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=reason)
        if self.private_repo and self.private_repo.coach_has_private_overlap(coach_id, start_at, end_at):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="coach_private_time_conflict")

    def create(self, request: CreateClassSessionRequest, actor_id: str) -> dict:
        values = request.model_dump()
        values["start_at"] = self._aware(request.start_at, "startAt")
        values["end_at"] = self._aware(request.end_at, "endAt")
        self._validate_schedule(
            course_id=request.course_id,
            coach_id=request.coach_profile_id,
            room_id=request.room_id,
            start_at=values["start_at"],
            end_at=values["end_at"],
            capacity=request.capacity,
        )
        class_session = self.session_repo.create(ClassSession(**values, status="draft", created_by=actor_id))
        return self.get(class_session.id)

    def get(self, session_id: UUID) -> dict:
        projected = self.session_repo.get_projected(session_id)
        if projected is None:
            raise self._missing("Class session")
        return projected

    def list_week(
        self,
        week_start: date,
        *,
        include_drafts: bool,
        coach_profile_id: UUID | None = None,
    ) -> tuple[list[dict], date]:
        start_at, end_at = self._week_bounds(week_start)
        return self.session_repo.list_week(
            start_at,
            end_at,
            include_drafts=include_drafts,
            coach_profile_id=coach_profile_id,
        ), week_start + timedelta(days=6)

    def update(self, session_id: UUID, request: UpdateClassSessionRequest) -> dict:
        current = self.session_repo.get_by_id(session_id, for_update=True)
        if current is None:
            raise self._missing("Class session")
        if current.status in {"cancelled", "completed"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="终态课次不能修改")
        changes = request.model_dump(exclude_unset=True)
        if "start_at" in changes:
            changes["start_at"] = self._aware(changes["start_at"], "startAt")
        if "end_at" in changes:
            changes["end_at"] = self._aware(changes["end_at"], "endAt")
        if KEY_FIELDS.intersection(changes) and self.session_repo.has_booking_history(session_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="课次已有预约历史")
        occupied = self.session_repo.occupied_count(session_id)
        capacity = changes.get("capacity", current.capacity)
        if capacity < occupied:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="容量不能低于已预约人数")
        values = {
            "course_id": changes.get("course_id", current.course_id),
            "coach_id": changes.get("coach_profile_id", current.coach_profile_id),
            "room_id": changes.get("room_id", current.room_id),
            "start_at": changes.get("start_at", current.start_at),
            "end_at": changes.get("end_at", current.end_at),
            "capacity": capacity,
        }
        self._validate_schedule(**values, exclude_id=session_id)
        for field, value in changes.items():
            setattr(current, field, value)
        self.session_repo.update(current)
        return self.get(session_id)

    def transition(self, session_id: UUID, action: str, *, now: datetime | None = None) -> dict:
        class_session = self.session_repo.get_by_id(session_id, for_update=True)
        if class_session is None:
            raise self._missing("Class session")
        allowed, target = TRANSITIONS[action]
        if class_session.status not in allowed:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"无法对 {class_session.status} 状态的课次执行 {action}")
        current_time = now or datetime.now(timezone.utc)
        if action == "complete" and current_time < class_session.end_at:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="课次尚未结束")
        if action in {"cancel", "complete"} and self.session_repo.has_reserved_booking(session_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该课次存在有效预约")
        class_session.status = target
        self.session_repo.update(class_session)
        return self.get(session_id)

    def copy_week(self, source_week_start: date, target_week_start: date, actor_id: str) -> tuple[list[dict], list[dict]]:
        source_start, source_end = self._week_bounds(source_week_start)
        self._week_bounds(target_week_start)
        if source_week_start == target_week_start:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="源周与目标周必须不同")
        offset = timedelta(days=(target_week_start - source_week_start).days)
        created: list[dict] = []
        conflicts: list[dict] = []
        for source in self.session_repo.source_week(source_start, source_end):
            target_start = source.start_at + offset
            target_end = source.end_at + offset
            reason = self._copy_conflict(source, target_start, target_end)
            if reason:
                conflicts.append({"source_session_id": source.id, "target_start_at": target_start, "reason": reason})
                continue
            copied = self.session_repo.create(
                ClassSession(
                    course_id=source.course_id,
                    coach_profile_id=source.coach_profile_id,
                    room_id=source.room_id,
                    start_at=target_start,
                    end_at=target_end,
                    capacity=source.capacity,
                    booking_open_hours_before=source.booking_open_hours_before,
                    booking_close_minutes_before=source.booking_close_minutes_before,
                    cancel_cutoff_minutes_before=source.cancel_cutoff_minutes_before,
                    status="draft",
                    source_session_id=source.id,
                    created_by=actor_id,
                )
            )
            created.append(self.get(copied.id))
        return created, conflicts

    def _copy_conflict(self, source: ClassSession, start_at: datetime, end_at: datetime) -> str | None:
        coach = self.coach_repo.get_by_id(source.coach_profile_id, for_update=True)
        room = self.room_repo.get_by_id(source.room_id, for_update=True)
        course = self.course_repo.get_by_id(source.course_id)
        if course is None or not course.enabled:
            return "course_disabled"
        if coach is None or not coach.enabled:
            return "coach_disabled"
        if room is None or not room.enabled:
            return "room_disabled"
        if source.capacity > room.capacity:
            return "room_capacity_exceeded"
        reason = self.session_repo.conflict_reason(
            coach_id=source.coach_profile_id,
            room_id=source.room_id,
            start_at=start_at,
            end_at=end_at,
        )
        if reason:
            return reason
        if self.private_repo and self.private_repo.coach_has_private_overlap(source.coach_profile_id, start_at, end_at):
            return "coach_private_time_conflict"
        return None
