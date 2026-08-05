from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.api.audit import record_audit
from app.domain.private_training import PrivateAvailability, PrivateBooking, PrivateLessonRecord
from app.infra.observability import business_span
from app.repositories.class_catalog import CoachProfileRepository
from app.repositories.member import MemberRepository
from app.repositories.private_training import PrivateTrainingRepository
from app.services.writeoff_service import WriteOffService

if TYPE_CHECKING:
    from app.api.deps.auth import CurrentUser


SHANGHAI = ZoneInfo("Asia/Shanghai")


class PrivateTrainingService:
    def __init__(
        self,
        session,
        repo: PrivateTrainingRepository,
        member_repo: MemberRepository,
        coach_repo: CoachProfileRepository,
        writeoff_service: WriteOffService,
    ):
        self.session = session
        self.repo = repo
        self.member_repo = member_repo
        self.coach_repo = coach_repo
        self.writeoff_service = writeoff_service

    def list_slots(
        self,
        *,
        actor: CurrentUser,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        coach_id: UUID | None = None,
    ) -> tuple[list[dict], int]:
        effective_coach_id = self._coach_scope(actor, coach_id, allow_member_any=True)
        return self.repo.list_slots(
            actor_role=actor.role, coach_id=effective_coach_id, date_from=date_from, date_to=date_to,
        )

    def list_bookings(
        self,
        *,
        actor: CurrentUser,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        member_id = UUID(actor.member_id) if actor.role == "member" and actor.member_id else None
        coach_id = UUID(actor.coach_profile_id) if actor.role == "coach" and actor.coach_profile_id else None
        return self.repo.list_bookings(member_id=member_id, coach_id=coach_id, status=status, skip=skip, limit=limit)

    def create_slot(self, payload, *, actor: CurrentUser, trace_id: str) -> dict:
        coach_id = self._coach_scope(actor, payload.coach_profile_id)
        with business_span("private_training.slot_create", coach_id=coach_id, actor_role=actor.role):
            return self._create_slot(coach_id, payload.start_at, payload.end_at, actor, trace_id=trace_id)

    def generate_week(self, payload, *, actor: CurrentUser, trace_id: str) -> tuple[list[dict], list[dict]]:
        coach_id = self._coach_scope(actor, payload.coach_profile_id)
        week_start = payload.week_start.astimezone(SHANGHAI).date()
        hour, minute = [int(part) for part in payload.start_time.split(":", 1)]
        created: list[dict] = []
        conflicts: list[dict] = []
        for weekday in sorted(set(payload.weekdays)):
            if weekday < 0 or weekday > 6:
                raise HTTPException(status_code=422, detail="weekday must be 0-6")
            local_start = datetime.combine(week_start + timedelta(days=weekday), time(hour, minute), SHANGHAI)
            start_at = local_start.astimezone(timezone.utc)
            end_at = start_at + timedelta(minutes=payload.duration_minutes)
            reason = self._slot_conflict(coach_id, start_at, end_at)
            if reason:
                conflicts.append({"start_at": start_at, "end_at": end_at, "reason": reason})
                continue
            created.append(self._create_slot(coach_id, start_at, end_at, actor, trace_id=trace_id, skip_conflict_check=True))
        return created, conflicts

    def update_slot(self, slot_id: UUID, payload, *, actor: CurrentUser, trace_id: str) -> dict:
        slot = self._slot(slot_id, for_update=True)
        self._authorize_coach_or_admin(slot.coach_profile_id, actor)
        if slot.status != "available":
            raise HTTPException(status_code=409, detail="Only available slot can be updated")
        coach_id = self._coach_scope(actor, payload.coach_profile_id or slot.coach_profile_id)
        reason = self._slot_conflict(coach_id, payload.start_at, payload.end_at, exclude_slot_id=slot.id)
        if reason:
            raise HTTPException(status_code=409, detail=reason)
        slot.coach_profile_id = coach_id
        slot.start_at = payload.start_at
        slot.end_at = payload.end_at
        slot.duration_minutes = self._duration_minutes(payload.start_at, payload.end_at)
        self.repo.update_slot(slot)
        self._audit("private_slot_update", actor, "private_availability", slot.id, trace_id=trace_id, after=self._slot_body(slot.id))
        return self._slot_body(slot.id)

    def cancel_slot(self, slot_id: UUID, *, actor: CurrentUser, trace_id: str) -> dict:
        slot = self._slot(slot_id, for_update=True)
        self._authorize_coach_or_admin(slot.coach_profile_id, actor)
        active, _ = self.repo.list_bookings(coach_id=slot.coach_profile_id, status="pending", limit=1)
        if slot.status == "locked" or any(item["availability_id"] == slot.id for item in active):
            raise HTTPException(status_code=409, detail="Slot has active booking")
        slot.status = "cancelled"
        self.repo.update_slot(slot)
        self._audit("private_slot_cancel", actor, "private_availability", slot.id, trace_id=trace_id, after=self._slot_body(slot.id))
        return self._slot_body(slot.id)

    def create_booking(
        self,
        payload,
        *,
        actor: CurrentUser,
        trace_id: str,
        now: datetime,
    ) -> dict:
        if actor.role != "member" or not actor.member_id:
            raise HTTPException(status_code=403, detail="Member role required")
        member_id = UUID(actor.member_id)
        with business_span("private_training.booking_create", member_id=member_id, actor_role=actor.role):
            member = self.member_repo.get_by_id(member_id)
            if not member:
                raise HTTPException(status_code=404, detail="Member not found")
            if member.status != "normal":
                raise HTTPException(status_code=409, detail="Member status does not allow booking")
            slot = self._slot(payload.availability_id, for_update=True)
            if slot.status != "available":
                raise HTTPException(status_code=409, detail="Private slot is not available")
            if slot.start_at <= self._utc(now):
                raise HTTPException(status_code=409, detail="Private slot is in the past")
            if self.repo.member_has_private_overlap(member_id, slot.start_at, slot.end_at):
                raise HTTPException(status_code=409, detail="Member has overlapping private booking")
            if self.repo.member_has_class_overlap(member_id, slot.start_at, slot.end_at):
                raise HTTPException(status_code=409, detail="Member has overlapping class booking")
            booking = self.repo.create_booking(PrivateBooking(
                availability_id=slot.id, member_id=member_id, coach_profile_id=slot.coach_profile_id,
                status="pending", member_message=payload.member_message,
                booked_by_id=actor.user_id, booked_by_role=actor.role, trace_id=trace_id,
            ))
            slot.status = "locked"
            self.repo.update_slot(slot)
            self._audit("private_booking_create", actor, "private_booking", booking.id, trace_id=trace_id, member_id=member_id, after=self.get_booking(booking.id, actor=actor))
            return self.get_booking(booking.id, actor=actor)

    def confirm_booking(self, booking_id: UUID, *, actor: CurrentUser, idempotency_key: str, trace_id: str, now: datetime, today: date) -> dict:
        booking, slot = self._booking_slot(booking_id)
        self._authorize_coach_or_admin(booking.coach_profile_id, actor)
        if booking.status != "pending":
            raise HTTPException(status_code=409, detail="Booking is not pending")
        event = self.writeoff_service.apply(
            member_id=booking.member_id, business_ref=str(booking.id), event_type="reserve_hold",
            user=actor, idempotency_key=idempotency_key, trace_id=trace_id, today=today,
            applicable_scope="private",
        )
        booking.status = "confirmed"
        booking.member_card_id = event.member_card_id
        booking.confirmed_at = self._utc(now)
        slot.status = "locked"
        self.repo.update_slot(slot)
        self.repo.update_booking(booking)
        self._audit("private_booking_confirm", actor, "private_booking", booking.id, trace_id=trace_id, member_id=booking.member_id, after=self.get_booking(booking.id, actor=actor), key=idempotency_key)
        return self.get_booking(booking.id, actor=actor)

    def reject_booking(self, booking_id: UUID, *, actor: CurrentUser, reason: str | None, trace_id: str, now: datetime) -> dict:
        booking, slot = self._booking_slot(booking_id)
        self._authorize_coach_or_admin(booking.coach_profile_id, actor)
        if booking.status != "pending":
            raise HTTPException(status_code=409, detail="Booking is not pending")
        booking.status = "rejected"
        booking.rejection_reason = reason
        self._terminalize(booking, actor, now)
        slot.status = "available"
        self.repo.update_slot(slot)
        self.repo.update_booking(booking)
        self._audit("private_booking_reject", actor, "private_booking", booking.id, trace_id=trace_id, member_id=booking.member_id, after=self.get_booking(booking.id, actor=actor))
        return self.get_booking(booking.id, actor=actor)

    def cancel_pending_booking(self, booking_id: UUID, *, actor: CurrentUser, reason: str | None, trace_id: str, now: datetime) -> dict:
        booking, slot = self._booking_slot(booking_id)
        if actor.role == "member":
            if not actor.member_id or str(booking.member_id) != actor.member_id:
                raise HTTPException(status_code=403, detail="Cannot cancel another member booking")
        elif actor.role != "admin":
            raise HTTPException(status_code=403, detail="Only member or admin may cancel pending private booking")
        if booking.status != "pending":
            raise HTTPException(status_code=409, detail="Only pending private booking can be cancelled")
        booking.status = "cancelled"
        booking.cancellation_reason = reason
        self._terminalize(booking, actor, now)
        slot.status = "available"
        self.repo.update_slot(slot)
        self.repo.update_booking(booking)
        self._audit("private_booking_cancel", actor, "private_booking", booking.id, trace_id=trace_id, member_id=booking.member_id, after=self.get_booking(booking.id, actor=actor))
        return self.get_booking(booking.id, actor=actor)

    def sign_in_booking(self, booking_id: UUID, payload, *, actor: CurrentUser, idempotency_key: str, trace_id: str, now: datetime, today: date) -> dict:
        booking, _ = self._booking_slot(booking_id)
        self._authorize_coach_or_admin(booking.coach_profile_id, actor)
        if booking.status != "confirmed":
            raise HTTPException(status_code=409, detail="Booking is not confirmed")
        self.writeoff_service.apply(
            member_id=booking.member_id, business_ref=str(booking.id), event_type="checkin_commit",
            user=actor, idempotency_key=idempotency_key, trace_id=trace_id, today=today,
        )
        current_time = self._utc(now)
        record = self.repo.create_lesson_record(PrivateLessonRecord(
            booking_id=booking.id, member_id=booking.member_id, coach_profile_id=booking.coach_profile_id,
            content=payload.content, consumed_hours=Decimal(payload.consumed_hours),
            member_status_notes=payload.member_status_notes, completed_at=current_time,
            trace_id=trace_id, created_by_id=actor.user_id, created_by_role=actor.role,
        ))
        booking.status = "completed"
        self._terminalize(booking, actor, now)
        self.repo.update_booking(booking)
        self._audit("private_booking_sign_in", actor, "private_lesson_record", record.id, trace_id=trace_id, member_id=booking.member_id, after=self.get_booking(booking.id, actor=actor), key=idempotency_key)
        return self.get_booking(booking.id, actor=actor)

    def get_booking(self, booking_id: UUID, *, actor: CurrentUser) -> dict:
        value = self.repo.get_projected_booking(booking_id)
        if not value:
            raise HTTPException(status_code=404, detail="Private booking not found")
        if actor.role == "member" and (not actor.member_id or str(value["member_id"]) != actor.member_id):
            raise HTTPException(status_code=403, detail="Forbidden")
        if actor.role == "coach" and (not actor.coach_profile_id or str(value["coach_profile_id"]) != actor.coach_profile_id):
            raise HTTPException(status_code=403, detail="Forbidden")
        return value

    def _create_slot(self, coach_id: UUID, start_at: datetime, end_at: datetime, actor: CurrentUser, *, trace_id: str, skip_conflict_check: bool = False) -> dict:
        if not skip_conflict_check:
            reason = self._slot_conflict(coach_id, start_at, end_at)
            if reason:
                raise HTTPException(status_code=409, detail=reason)
        coach = self.coach_repo.get_by_id(coach_id)
        if not coach or not coach.enabled:
            raise HTTPException(status_code=404, detail="Enabled coach not found")
        slot = self.repo.create_slot(PrivateAvailability(
            coach_profile_id=coach_id, start_at=start_at, end_at=end_at,
            duration_minutes=self._duration_minutes(start_at, end_at), status="available",
            created_by_id=actor.user_id, created_by_role=actor.role,
        ))
        body = self._slot_body(slot.id)
        self._audit("private_slot_create", actor, "private_availability", slot.id, trace_id=trace_id, after=body)
        return body

    def _slot_conflict(self, coach_id: UUID, start_at: datetime, end_at: datetime, *, exclude_slot_id: UUID | None = None) -> str | None:
        if end_at <= start_at:
            return "invalid_time_range"
        if self.repo.coach_has_private_overlap(coach_id, start_at, end_at, exclude_slot_id=exclude_slot_id):
            return "private_slot_time_conflict"
        if self.repo.coach_has_class_overlap(coach_id, start_at, end_at):
            return "coach_class_time_conflict"
        return None

    def _slot_body(self, slot_id: UUID) -> dict:
        rows, _ = self.repo.list_slots(actor_role="admin")
        for row in rows:
            if row["id"] == slot_id:
                return row
        raise HTTPException(status_code=404, detail="Private slot not found")

    def _slot(self, slot_id: UUID, *, for_update: bool = False) -> PrivateAvailability:
        slot = self.repo.get_slot(slot_id, for_update=for_update)
        if not slot:
            raise HTTPException(status_code=404, detail="Private slot not found")
        return slot

    def _booking_slot(self, booking_id: UUID) -> tuple[PrivateBooking, PrivateAvailability]:
        booking = self.repo.get_booking(booking_id, for_update=True)
        if not booking:
            raise HTTPException(status_code=404, detail="Private booking not found")
        slot = self._slot(booking.availability_id, for_update=True)
        return booking, slot

    def _coach_scope(self, actor: CurrentUser, requested: UUID | None, *, allow_member_any: bool = False) -> UUID | None:
        if actor.role == "admin":
            return requested
        if actor.role == "coach" and actor.coach_profile_id:
            if requested and str(requested) != actor.coach_profile_id:
                raise HTTPException(status_code=403, detail="Cannot manage another coach private slots")
            return UUID(actor.coach_profile_id)
        if actor.role == "member" and allow_member_any:
            return requested
        raise HTTPException(status_code=403, detail="Forbidden")

    @staticmethod
    def _authorize_coach_or_admin(coach_id: UUID, actor: CurrentUser) -> None:
        if actor.role == "admin":
            return
        if actor.role == "coach" and actor.coach_profile_id and str(coach_id) == actor.coach_profile_id:
            return
        raise HTTPException(status_code=403, detail="Only admin or owning coach may operate")

    @staticmethod
    def _terminalize(booking: PrivateBooking, actor: CurrentUser, now: datetime) -> None:
        booking.terminal_by_id = actor.user_id
        booking.terminal_by_role = actor.role
        booking.terminal_at = PrivateTrainingService._utc(now)

    @staticmethod
    def _duration_minutes(start_at: datetime, end_at: datetime) -> int:
        return int((end_at - start_at).total_seconds() // 60)

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    def _audit(self, action: str, actor: CurrentUser, object_type: str, object_id: UUID, *, trace_id: str, member_id: UUID | None = None, after: dict | None = None, key: str | None = None) -> None:
        record_audit(
            self.session, trace_id=trace_id, idempotency_key=key,
            action=action, user=actor, object_type=object_type, object_id=str(object_id),
            member_id=member_id, after_state=after,
        )
