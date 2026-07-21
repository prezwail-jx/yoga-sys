from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.class_booking import ClassBooking
from app.domain.class_session import ClassSession
from app.domain.coach_profile import CoachProfile
from app.domain.course import Course
from app.domain.member import Member
from app.domain.room import Room


OCCUPIED_STATUSES = ("reserved", "checked_in")


class ClassBookingRepository:
    def __init__(self, session: Session):
        self.session = session

    def lock_member(self, member_id: UUID) -> Member | None:
        return self.session.scalars(
            select(Member)
            .where(Member.id == member_id, Member.deleted_at.is_(None))
            .with_for_update()
        ).first()

    def get_by_id(self, booking_id: UUID, *, for_update: bool = False) -> ClassBooking | None:
        statement = select(ClassBooking).where(ClassBooking.id == booking_id)
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalars(statement).first()

    def create(self, booking: ClassBooking) -> ClassBooking:
        self.session.add(booking)
        self.session.flush()
        return booking

    def update(self, booking: ClassBooking) -> ClassBooking:
        self.session.add(booking)
        self.session.flush()
        return booking

    def occupied_count(self, session_id: UUID) -> int:
        return int(
            self.session.scalar(
                select(func.count()).select_from(ClassBooking).where(
                    ClassBooking.class_session_id == session_id,
                    ClassBooking.status.in_(OCCUPIED_STATUSES),
                )
            )
            or 0
        )

    def has_active_booking(self, session_id: UUID, member_id: UUID) -> bool:
        return self.session.scalar(
            select(ClassBooking.id).where(
                ClassBooking.class_session_id == session_id,
                ClassBooking.member_id == member_id,
                ClassBooking.status.in_(OCCUPIED_STATUSES),
            ).limit(1)
        ) is not None

    def has_member_overlap(
        self,
        member_id: UUID,
        start_at: datetime,
        end_at: datetime,
        *,
        exclude_session_id: UUID | None = None,
    ) -> bool:
        filters = [
            ClassBooking.member_id == member_id,
            ClassBooking.status.in_(OCCUPIED_STATUSES),
            ClassSession.start_at < end_at,
            ClassSession.end_at > start_at,
        ]
        if exclude_session_id is not None:
            filters.append(ClassSession.id != exclude_session_id)
        return self.session.scalar(
            select(ClassBooking.id)
            .join(ClassSession, ClassSession.id == ClassBooking.class_session_id)
            .where(*filters)
            .limit(1)
        ) is not None

    def list_for_session(self, session_id: UUID, *, for_update: bool = False) -> list[ClassBooking]:
        statement = (
            select(ClassBooking)
            .where(ClassBooking.class_session_id == session_id)
            .order_by(ClassBooking.member_id, ClassBooking.id)
        )
        if for_update:
            statement = statement.with_for_update()
        return list(self.session.scalars(statement).all())

    def list_for_member(
        self,
        member_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        filters = [ClassBooking.member_id == member_id]
        total = self.session.scalar(select(func.count()).select_from(ClassBooking).where(*filters)) or 0
        rows = self.session.execute(
            self._projection().where(*filters).order_by(
                ClassSession.start_at.desc(), ClassBooking.id.desc()
            ).offset(skip).limit(limit)
        ).all()
        return [self.as_dict(row) for row in rows], int(total)

    def get_projected(self, booking_id: UUID) -> dict | None:
        row = self.session.execute(
            self._projection().where(ClassBooking.id == booking_id)
        ).first()
        return self.as_dict(row) if row else None

    def list_projected_for_session(self, session_id: UUID) -> list[dict]:
        rows = self.session.execute(
            self._projection().where(ClassBooking.class_session_id == session_id).order_by(
                Member.name, ClassBooking.member_id, ClassBooking.id
            )
        ).all()
        return [self.as_dict(row) for row in rows]

    @staticmethod
    def _projection():
        return (
            select(
                ClassBooking,
                Member.name.label("member_name"),
                Course.name.label("course_name"),
                CoachProfile.name.label("coach_name"),
                Room.name.label("room_name"),
                ClassSession.start_at,
                ClassSession.end_at,
                ClassSession.status.label("session_status"),
            )
            .join(Member, Member.id == ClassBooking.member_id)
            .join(ClassSession, ClassSession.id == ClassBooking.class_session_id)
            .join(Course, Course.id == ClassSession.course_id)
            .join(CoachProfile, CoachProfile.id == ClassSession.coach_profile_id)
            .join(Room, Room.id == ClassSession.room_id)
        )

    @staticmethod
    def as_dict(row) -> dict:
        booking, member_name, course_name, coach_name, room_name, start_at, end_at, session_status = row
        return {
            "id": booking.id,
            "class_session_id": booking.class_session_id,
            "member_id": booking.member_id,
            "member_name": member_name,
            "course_name": course_name,
            "coach_name": coach_name,
            "room_name": room_name,
            "start_at": start_at,
            "end_at": end_at,
            "session_status": session_status,
            "status": booking.status,
            "booked_by_id": booking.booked_by_id,
            "booked_by_role": booking.booked_by_role,
            "booked_at": booking.booked_at,
            "terminal_by_id": booking.terminal_by_id,
            "terminal_by_role": booking.terminal_by_role,
            "terminal_at": booking.terminal_at,
            "cancellation_reason": booking.cancellation_reason,
            "trace_id": booking.trace_id,
            "created_at": booking.created_at,
            "updated_at": booking.updated_at,
        }
