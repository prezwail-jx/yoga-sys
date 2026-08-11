from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.class_booking import ClassBooking
from app.domain.class_session import ClassSession
from app.domain.coach_profile import CoachProfile
from app.domain.member import Member
from app.domain.private_training import PrivateAvailability, PrivateBooking, PrivateLessonRecord


ACTIVE_SLOT_STATUSES = ("available", "locked")
ACTIVE_BOOKING_STATUSES = ("pending", "confirmed")
ACTIVE_CLASS_SESSION_STATUSES = ("draft", "published", "paused")
ACTIVE_CLASS_BOOKING_STATUSES = ("reserved", "checked_in")


class PrivateTrainingRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_slot(self, slot_id: UUID, *, for_update: bool = False) -> PrivateAvailability | None:
        stmt = select(PrivateAvailability).where(PrivateAvailability.id == slot_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.scalars(stmt).first()

    def get_booking(self, booking_id: UUID, *, for_update: bool = False) -> PrivateBooking | None:
        stmt = select(PrivateBooking).where(PrivateBooking.id == booking_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.scalars(stmt).first()

    def create_slot(self, slot: PrivateAvailability) -> PrivateAvailability:
        self.session.add(slot)
        self.session.flush()
        self.session.refresh(slot)
        return slot

    def update_slot(self, slot: PrivateAvailability) -> PrivateAvailability:
        self.session.add(slot)
        self.session.flush()
        self.session.refresh(slot)
        return slot

    def create_booking(self, booking: PrivateBooking) -> PrivateBooking:
        self.session.add(booking)
        self.session.flush()
        self.session.refresh(booking)
        return booking

    def slot_has_active_booking(self, slot_id: UUID) -> bool:
        return self.session.scalar(
            select(PrivateBooking.id).where(
                PrivateBooking.availability_id == slot_id,
                PrivateBooking.status.in_(ACTIVE_BOOKING_STATUSES),
            ).limit(1)
        ) is not None

    def update_booking(self, booking: PrivateBooking) -> PrivateBooking:
        self.session.add(booking)
        self.session.flush()
        self.session.refresh(booking)
        return booking

    def create_lesson_record(self, record: PrivateLessonRecord) -> PrivateLessonRecord:
        self.session.add(record)
        self.session.flush()
        self.session.refresh(record)
        return record

    def coach_has_private_overlap(
        self, coach_id: UUID, start_at: datetime, end_at: datetime, *, exclude_slot_id: UUID | None = None
    ) -> bool:
        filters = [
            PrivateAvailability.coach_profile_id == coach_id,
            PrivateAvailability.status.in_(ACTIVE_SLOT_STATUSES),
            PrivateAvailability.start_at < end_at,
            PrivateAvailability.end_at > start_at,
        ]
        if exclude_slot_id:
            filters.append(PrivateAvailability.id != exclude_slot_id)
        return self.session.scalar(select(PrivateAvailability.id).where(*filters).limit(1)) is not None

    def coach_has_class_overlap(self, coach_id: UUID, start_at: datetime, end_at: datetime) -> bool:
        return self.session.scalar(
            select(ClassSession.id).where(
                ClassSession.coach_profile_id == coach_id,
                ClassSession.status.in_(ACTIVE_CLASS_SESSION_STATUSES),
                ClassSession.start_at < end_at,
                ClassSession.end_at > start_at,
            ).limit(1)
        ) is not None

    def member_has_private_overlap(
        self, member_id: UUID, start_at: datetime, end_at: datetime, *, exclude_booking_id: UUID | None = None
    ) -> bool:
        filters = [
            PrivateBooking.member_id == member_id,
            PrivateBooking.status.in_(ACTIVE_BOOKING_STATUSES),
            PrivateAvailability.start_at < end_at,
            PrivateAvailability.end_at > start_at,
        ]
        if exclude_booking_id:
            filters.append(PrivateBooking.id != exclude_booking_id)
        return self.session.scalar(
            select(PrivateBooking.id)
            .join(PrivateAvailability, PrivateAvailability.id == PrivateBooking.availability_id)
            .where(*filters)
            .limit(1)
        ) is not None

    def member_has_class_overlap(self, member_id: UUID, start_at: datetime, end_at: datetime) -> bool:
        return self.session.scalar(
            select(ClassBooking.id)
            .join(ClassSession, ClassSession.id == ClassBooking.class_session_id)
            .where(
                ClassBooking.member_id == member_id,
                ClassBooking.status.in_(ACTIVE_CLASS_BOOKING_STATUSES),
                ClassSession.start_at < end_at,
                ClassSession.end_at > start_at,
            )
            .limit(1)
        ) is not None

    def list_slots(
        self,
        *,
        actor_role: str,
        coach_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[dict], int]:
        filters = []
        if actor_role == "member":
            filters.append(PrivateAvailability.status == "available")
        elif coach_id:
            filters.append(PrivateAvailability.coach_profile_id == coach_id)
        if date_from:
            filters.append(PrivateAvailability.start_at >= date_from)
        if date_to:
            filters.append(PrivateAvailability.start_at < date_to)
        total = self.session.scalar(select(func.count()).select_from(PrivateAvailability).where(*filters)) or 0
        rows = self.session.execute(
            select(PrivateAvailability, CoachProfile.name.label("coach_name"))
            .join(CoachProfile, CoachProfile.id == PrivateAvailability.coach_profile_id)
            .where(*filters)
            .order_by(PrivateAvailability.start_at, PrivateAvailability.id)
        ).all()
        return [self.slot_as_dict(row) for row in rows], int(total)

    def list_bookings(
        self,
        *,
        member_id: UUID | None = None,
        coach_id: UUID | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        filters = []
        if member_id:
            filters.append(PrivateBooking.member_id == member_id)
        if coach_id:
            filters.append(PrivateBooking.coach_profile_id == coach_id)
        if status:
            filters.append(PrivateBooking.status == status)
        total = self.session.scalar(select(func.count()).select_from(PrivateBooking).where(*filters)) or 0
        rows = self.session.execute(
            self._booking_projection().where(*filters).order_by(PrivateAvailability.start_at.desc(), PrivateBooking.id.desc())
            .offset(skip).limit(limit)
        ).all()
        return [self.booking_as_dict(row) for row in rows], int(total)

    def get_projected_booking(self, booking_id: UUID) -> dict | None:
        row = self.session.execute(self._booking_projection().where(PrivateBooking.id == booking_id)).first()
        return self.booking_as_dict(row) if row else None

    @staticmethod
    def slot_as_dict(row) -> dict:
        slot, coach_name = row
        return {
            "id": slot.id,
            "coach_profile_id": slot.coach_profile_id,
            "coach_name": coach_name,
            "start_at": slot.start_at,
            "end_at": slot.end_at,
            "duration_minutes": slot.duration_minutes,
            "status": slot.status,
            "created_by_id": slot.created_by_id,
            "created_by_role": slot.created_by_role,
            "created_at": slot.created_at,
            "updated_at": slot.updated_at,
        }

    @staticmethod
    def _booking_projection():
        return (
            select(
                PrivateBooking,
                PrivateAvailability.start_at,
                PrivateAvailability.end_at,
                PrivateAvailability.duration_minutes,
                Member.name.label("member_name"),
                CoachProfile.name.label("coach_name"),
            )
            .join(PrivateAvailability, PrivateAvailability.id == PrivateBooking.availability_id)
            .join(Member, Member.id == PrivateBooking.member_id)
            .join(CoachProfile, CoachProfile.id == PrivateBooking.coach_profile_id)
        )

    @staticmethod
    def booking_as_dict(row) -> dict:
        booking, start_at, end_at, duration_minutes, member_name, coach_name = row
        return {
            "id": booking.id,
            "availability_id": booking.availability_id,
            "member_id": booking.member_id,
            "member_name": member_name,
            "coach_profile_id": booking.coach_profile_id,
            "coach_name": coach_name,
            "member_card_id": booking.member_card_id,
            "start_at": start_at,
            "end_at": end_at,
            "duration_minutes": duration_minutes,
            "status": booking.status,
            "member_message": booking.member_message,
            "rejection_reason": booking.rejection_reason,
            "cancellation_reason": booking.cancellation_reason,
            "booked_by_id": booking.booked_by_id,
            "booked_by_role": booking.booked_by_role,
            "confirmed_at": booking.confirmed_at,
            "terminal_by_id": booking.terminal_by_id,
            "terminal_by_role": booking.terminal_by_role,
            "terminal_at": booking.terminal_at,
            "trace_id": booking.trace_id,
            "created_at": booking.created_at,
            "updated_at": booking.updated_at,
        }
