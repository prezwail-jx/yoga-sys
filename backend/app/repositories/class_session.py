from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.domain.class_booking import ClassBooking
from app.domain.class_session import ClassSession
from app.domain.coach_profile import CoachProfile
from app.domain.course import Course
from app.domain.room import Room


ACTIVE_SESSION_STATUSES = ("draft", "published", "paused")
OCCUPIED_BOOKING_STATUSES = ("reserved", "checked_in")


class ClassSessionRepository:
    def __init__(self, session: Session):
        self.session = session

    def _projection(self):
        occupied = func.coalesce(
            func.sum(case((ClassBooking.status.in_(OCCUPIED_BOOKING_STATUSES), 1), else_=0)),
            0,
        ).label("booked_count")
        return (
            select(
                ClassSession,
                Course.name.label("course_name"),
                CoachProfile.name.label("coach_name"),
                Room.name.label("room_name"),
                occupied,
            )
            .join(Course, Course.id == ClassSession.course_id)
            .join(CoachProfile, CoachProfile.id == ClassSession.coach_profile_id)
            .join(Room, Room.id == ClassSession.room_id)
            .outerjoin(ClassBooking, ClassBooking.class_session_id == ClassSession.id)
            .group_by(ClassSession.id, Course.name, CoachProfile.name, Room.name)
        )

    @staticmethod
    def as_dict(row) -> dict:
        session, course_name, coach_name, room_name, booked_count = row
        count = int(booked_count)
        return {
            "id": session.id,
            "course_id": session.course_id,
            "coach_profile_id": session.coach_profile_id,
            "room_id": session.room_id,
            "course_name": course_name,
            "coach_name": coach_name,
            "room_name": room_name,
            "start_at": session.start_at,
            "end_at": session.end_at,
            "capacity": session.capacity,
            "booking_open_hours_before": session.booking_open_hours_before,
            "booking_close_minutes_before": session.booking_close_minutes_before,
            "cancel_cutoff_minutes_before": session.cancel_cutoff_minutes_before,
            "status": session.status,
            "source_session_id": session.source_session_id,
            "created_by": session.created_by,
            "booked_count": count,
            "remaining_capacity": max(session.capacity - count, 0),
            "is_full": count >= session.capacity,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        }

    def get_by_id(self, session_id: UUID, *, for_update: bool = False) -> ClassSession | None:
        statement = select(ClassSession).where(ClassSession.id == session_id)
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalars(statement).first()

    def get_projected(self, session_id: UUID) -> dict | None:
        row = self.session.execute(self._projection().where(ClassSession.id == session_id)).first()
        return self.as_dict(row) if row else None

    def list_week(
        self,
        start_at: datetime,
        end_at: datetime,
        *,
        include_drafts: bool,
        coach_profile_id: UUID | None = None,
    ) -> list[dict]:
        statement = self._projection().where(
            ClassSession.start_at >= start_at,
            ClassSession.start_at < end_at,
        )
        if not include_drafts:
            statement = statement.where(ClassSession.status != "draft")
        if coach_profile_id is not None:
            statement = statement.where(ClassSession.coach_profile_id == coach_profile_id)
        rows = self.session.execute(statement.order_by(ClassSession.start_at, ClassSession.id)).all()
        return [self.as_dict(row) for row in rows]

    def source_week(self, start_at: datetime, end_at: datetime) -> list[ClassSession]:
        return list(
            self.session.scalars(
                select(ClassSession)
                .where(
                    ClassSession.start_at >= start_at,
                    ClassSession.start_at < end_at,
                    ClassSession.status != "cancelled",
                )
                .order_by(ClassSession.start_at, ClassSession.id)
            ).all()
        )

    def create(self, class_session: ClassSession) -> ClassSession:
        self.session.add(class_session)
        self.session.flush()
        return class_session

    def update(self, class_session: ClassSession) -> ClassSession:
        self.session.add(class_session)
        self.session.flush()
        return class_session

    def conflict_reason(
        self,
        *,
        coach_id: UUID,
        room_id: UUID,
        start_at: datetime,
        end_at: datetime,
        exclude_id: UUID | None = None,
    ) -> str | None:
        base = [
            ClassSession.status.in_(ACTIVE_SESSION_STATUSES),
            ClassSession.start_at < end_at,
            ClassSession.end_at > start_at,
        ]
        if exclude_id is not None:
            base.append(ClassSession.id != exclude_id)
        if self.session.scalar(select(ClassSession.id).where(*base, ClassSession.coach_profile_id == coach_id).limit(1)):
            return "coach_time_conflict"
        if self.session.scalar(select(ClassSession.id).where(*base, ClassSession.room_id == room_id).limit(1)):
            return "room_time_conflict"
        return None

    def occupied_count(self, session_id: UUID) -> int:
        return int(
            self.session.scalar(
                select(func.count()).select_from(ClassBooking).where(
                    ClassBooking.class_session_id == session_id,
                    ClassBooking.status.in_(OCCUPIED_BOOKING_STATUSES),
                )
            )
            or 0
        )

    def has_booking_history(self, session_id: UUID) -> bool:
        return self.session.scalar(
            select(ClassBooking.id).where(ClassBooking.class_session_id == session_id).limit(1)
        ) is not None

    def has_reserved_booking(self, session_id: UUID) -> bool:
        return self.session.scalar(
            select(ClassBooking.id).where(
                ClassBooking.class_session_id == session_id,
                ClassBooking.status == "reserved",
            ).limit(1)
        ) is not None

    def update_status(self, class_session: ClassSession, status: str) -> ClassSession:
        class_session.status = status
        return self.update(class_session)
