from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status

from app.api.audit import record_audit
from app.domain.class_booking import ClassBooking
from app.infra.observability import business_span
from app.repositories.class_booking import ClassBookingRepository
from app.repositories.class_session import ClassSessionRepository
from app.services.writeoff_service import WriteOffService
from app.repositories.private_training import PrivateTrainingRepository

if TYPE_CHECKING:
    from app.api.deps.auth import CurrentUser


class ClassBookingService:
    def __init__(
        self,
        session,
        booking_repo: ClassBookingRepository,
        session_repo: ClassSessionRepository,
        writeoff_service: WriteOffService,
        private_repo: PrivateTrainingRepository | None = None,
    ):
        self.session = session
        self.booking_repo = booking_repo
        self.session_repo = session_repo
        self.writeoff_service = writeoff_service
        self.private_repo = private_repo

    def create(
        self,
        *,
        session_id: UUID,
        actor: CurrentUser,
        idempotency_key: str,
        trace_id: str,
        member_id: UUID | None = None,
        now: datetime | None = None,
        today: date | None = None,
    ) -> dict:
        effective_member_id = self._booking_member(actor, member_id)
        current_time = self._utc(now)
        with business_span(
            "class_booking.create", session_id=session_id,
            member_id=effective_member_id, actor_role=actor.role,
        ):
            # The lock order is invariant across booking writes: member, then session.
            member = self.booking_repo.lock_member(effective_member_id)
            if member is None:
                raise HTTPException(status_code=404, detail="Member not found")
            class_session = self.session_repo.get_by_id(session_id, for_update=True)
            if class_session is None:
                raise HTTPException(status_code=404, detail="Class session not found")
            if member.status != "normal":
                raise HTTPException(status_code=409, detail="Member status does not allow booking")
            if class_session.status != "published":
                raise HTTPException(status_code=409, detail="Class session is not published")
            if actor.role == "member":
                opens_at = class_session.start_at - timedelta(hours=class_session.booking_open_hours_before)
                closes_at = class_session.start_at - timedelta(minutes=class_session.booking_close_minutes_before)
                if not opens_at <= current_time < closes_at:
                    raise HTTPException(status_code=409, detail="Class booking window is closed")
            if self.booking_repo.occupied_count(session_id) >= class_session.capacity:
                raise HTTPException(status_code=409, detail="Class session is full")
            if self.booking_repo.has_active_booking(session_id, effective_member_id):
                raise HTTPException(status_code=409, detail="Member already has an active booking")
            if self.booking_repo.has_member_overlap(
                effective_member_id, class_session.start_at, class_session.end_at,
                exclude_session_id=session_id,
            ):
                raise HTTPException(status_code=409, detail="Member has an overlapping class booking")
            if self.private_repo and self.private_repo.member_has_private_overlap(
                effective_member_id, class_session.start_at, class_session.end_at,
            ):
                raise HTTPException(status_code=409, detail="Member has an overlapping private booking")
            booking = self.booking_repo.create(ClassBooking(
                class_session_id=session_id,
                member_id=effective_member_id,
                status="reserved",
                booked_by_id=actor.user_id,
                booked_by_role=actor.role,
                trace_id=trace_id,
            ))
            self.writeoff_service.apply(
                member_id=effective_member_id,
                business_ref=str(booking.id),
                event_type="reserve_hold",
                user=actor,
                idempotency_key=idempotency_key,
                trace_id=trace_id,
                today=today or current_time.date(),
                course_id=class_session.course_id,
            )
            self._audit("class_booking_create", booking, actor, trace_id, idempotency_key)
            return self.get(booking.id)

    def cancel(
        self,
        booking_id: UUID,
        *,
        actor: CurrentUser,
        idempotency_key: str,
        trace_id: str,
        reason: str | None = None,
        now: datetime | None = None,
        today: date | None = None,
    ) -> dict:
        current_time = self._utc(now)
        with business_span("class_booking.cancel", booking_id=booking_id, actor_role=actor.role):
            booking, class_session = self._lock_booking_session(booking_id)
            self._authorize_owner_or_admin(booking, actor)
            if booking.status != "reserved":
                raise HTTPException(status_code=409, detail="Booking is not reserved")
            if class_session.status in {"cancelled", "completed"}:
                raise HTTPException(status_code=409, detail="Class session is terminal")
            cutoff = class_session.start_at - timedelta(minutes=class_session.cancel_cutoff_minutes_before)
            if actor.role == "member" and current_time > cutoff:
                raise HTTPException(status_code=409, detail="Class cancellation cutoff has passed")
            self.writeoff_service.apply(
                member_id=booking.member_id, business_ref=str(booking.id),
                event_type="cancel_refund", user=actor, idempotency_key=idempotency_key,
                trace_id=trace_id, today=today or current_time.date(),
            )
            self._terminalize(booking, "cancelled", actor, current_time, reason)
            self._audit("class_booking_cancel", booking, actor, trace_id, idempotency_key)
            return self.get(booking.id)

    def check_in(
        self,
        booking_id: UUID,
        *,
        actor: CurrentUser,
        idempotency_key: str,
        trace_id: str,
        now: datetime | None = None,
        today: date | None = None,
    ) -> dict:
        current_time = self._utc(now)
        with business_span("class_booking.check_in", booking_id=booking_id, actor_role=actor.role):
            booking, class_session = self._lock_booking_session(booking_id)
            coach_id = getattr(actor, "coach_profile_id", None)
            if actor.role != "admin" and not (
                actor.role == "coach" and coach_id and str(class_session.coach_profile_id) == str(coach_id)
            ):
                raise HTTPException(status_code=403, detail="Only admin or the assigned coach may check in")
            if booking.status != "reserved":
                raise HTTPException(status_code=409, detail="Booking is not reserved")
            if class_session.status != "published":
                raise HTTPException(status_code=409, detail="Class session is not published")
            if current_time < class_session.start_at - timedelta(minutes=30):
                raise HTTPException(status_code=409, detail="Check-in has not opened")
            self.writeoff_service.apply(
                member_id=booking.member_id, business_ref=str(booking.id),
                event_type="checkin_commit", user=actor, idempotency_key=idempotency_key,
                trace_id=trace_id, today=today or current_time.date(),
            )
            self._terminalize(booking, "checked_in", actor, current_time)
            self._audit("class_booking_check_in", booking, actor, trace_id, idempotency_key)
            return self.get(booking.id)

    def cancel_session(
        self,
        session_id: UUID,
        *,
        actor: CurrentUser,
        idempotency_key: str,
        trace_id: str,
        reason: str | None = None,
        now: datetime | None = None,
        today: date | None = None,
    ) -> dict:
        self._require_admin(actor)
        current_time = self._utc(now)
        with business_span("class_booking.cancel_session", session_id=session_id, actor_role=actor.role):
            class_session = self._session(session_id)
            if class_session.status not in {"draft", "published", "paused"}:
                raise HTTPException(status_code=409, detail="Class session cannot be cancelled")
            bookings = self.booking_repo.list_for_session(session_id, for_update=True)
            if any(booking.status == "checked_in" for booking in bookings):
                raise HTTPException(status_code=409, detail="Checked-in booking prevents session cancellation")
            for booking in bookings:
                if booking.status != "reserved":
                    continue
                key = self._child_key(idempotency_key, booking.id)
                self.writeoff_service.apply(
                    member_id=booking.member_id, business_ref=str(booking.id),
                    event_type="cancel_refund", user=actor, idempotency_key=key,
                    trace_id=trace_id, today=today or current_time.date(), force_refund=True,
                )
                self._terminalize(booking, "cancelled", actor, current_time, reason)
                self._audit(
                    "class_booking_venue_cancel", booking, actor, trace_id, key,
                    reason="venue_cancel_force_refund",
                )
            self.session_repo.update_status(class_session, "cancelled")
            projected = self.session_repo.get_projected(session_id)
            self._audit_session(
                "class_session_cancel", session_id, actor, trace_id,
                idempotency_key, "cancelled",
            )
            return projected

    def complete_session(
        self,
        session_id: UUID,
        *,
        actor: CurrentUser,
        idempotency_key: str,
        trace_id: str,
        now: datetime | None = None,
        today: date | None = None,
    ) -> dict:
        self._require_admin(actor)
        current_time = self._utc(now)
        with business_span("class_booking.complete_session", session_id=session_id, actor_role=actor.role):
            class_session = self._session(session_id)
            if class_session.status not in {"published", "paused"}:
                raise HTTPException(status_code=409, detail="Class session cannot be completed")
            if current_time < class_session.end_at:
                raise HTTPException(status_code=409, detail="Class session has not ended")
            for booking in self.booking_repo.list_for_session(session_id, for_update=True):
                if booking.status != "reserved":
                    continue
                key = self._child_key(idempotency_key, booking.id)
                self.writeoff_service.apply(
                    member_id=booking.member_id, business_ref=str(booking.id),
                    event_type="absence_commit", user=actor, idempotency_key=key,
                    trace_id=trace_id, today=today or current_time.date(),
                )
                self._terminalize(booking, "absent", actor, current_time)
                self._audit("class_booking_absence", booking, actor, trace_id, key)
            self.session_repo.update_status(class_session, "completed")
            projected = self.session_repo.get_projected(session_id)
            self._audit_session(
                "class_session_complete", session_id, actor, trace_id,
                idempotency_key, "completed",
            )
            return projected

    def get(self, booking_id: UUID) -> dict:
        projected = self.booking_repo.get_projected(booking_id)
        if projected is None:
            raise HTTPException(status_code=404, detail="Class booking not found")
        return projected

    def list_session(self, session_id: UUID) -> list[dict]:
        if self.session_repo.get_by_id(session_id) is None:
            raise HTTPException(status_code=404, detail="Class session not found")
        return self.booking_repo.list_projected_for_session(session_id)

    def assert_session_roster_readable(self, session_id: UUID, actor: CurrentUser) -> None:
        class_session = self.session_repo.get_by_id(session_id)
        if class_session is None:
            raise HTTPException(status_code=404, detail="Class session not found")
        if actor.role == "admin":
            return
        if (
            actor.role == "coach" and actor.coach_profile_id
            and str(class_session.coach_profile_id) == str(actor.coach_profile_id)
        ):
            return
        raise HTTPException(status_code=403, detail="Class session roster is forbidden")

    def list_member(
        self,
        *,
        actor: CurrentUser,
        member_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        effective_member_id = self._booking_member(actor, member_id)
        return self.booking_repo.list_for_member(effective_member_id, skip=skip, limit=limit)

    def _locked_booking(self, booking_id: UUID) -> ClassBooking:
        booking = self.booking_repo.get_by_id(booking_id, for_update=True)
        if booking is None:
            raise HTTPException(status_code=404, detail="Class booking not found")
        return booking

    def _lock_booking_session(self, booking_id: UUID):
        existing = self.booking_repo.get_by_id(booking_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Class booking not found")
        class_session = self._session(existing.class_session_id)
        booking = self._locked_booking(booking_id)
        return booking, class_session

    def _session(self, session_id: UUID):
        class_session = self.session_repo.get_by_id(session_id, for_update=True)
        if class_session is None:
            raise HTTPException(status_code=404, detail="Class session not found")
        return class_session

    @staticmethod
    def _booking_member(actor: CurrentUser, member_id: UUID | None) -> UUID:
        if actor.role == "member":
            if not actor.member_id:
                raise HTTPException(status_code=403, detail="Member identity is not bound")
            bound_member_id = UUID(str(actor.member_id))
            if member_id is not None and member_id != bound_member_id:
                raise HTTPException(status_code=403, detail="Member cannot book for another member")
            return bound_member_id
        if actor.role == "admin" and member_id is not None:
            return member_id
        raise HTTPException(status_code=403, detail="Admin memberId is required")

    @staticmethod
    def _authorize_owner_or_admin(booking: ClassBooking, actor: CurrentUser) -> None:
        if actor.role == "admin":
            return
        if actor.role != "member" or not actor.member_id or str(booking.member_id) != str(actor.member_id):
            raise HTTPException(status_code=403, detail="Booking belongs to another member")

    @staticmethod
    def _require_admin(actor: CurrentUser) -> None:
        if actor.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    def _terminalize(
        self,
        booking: ClassBooking,
        target: str,
        actor: CurrentUser,
        at: datetime,
        reason: str | None = None,
    ) -> None:
        booking.status = target
        booking.terminal_by_id = actor.user_id
        booking.terminal_by_role = actor.role
        booking.terminal_at = at
        booking.cancellation_reason = reason if target == "cancelled" else None
        self.booking_repo.update(booking)

    def _audit(
        self,
        action: str,
        booking: ClassBooking,
        actor: CurrentUser,
        trace_id: str,
        idempotency_key: str,
        reason: str | None = None,
    ) -> None:
        record_audit(
            self.session, trace_id=trace_id, idempotency_key=idempotency_key,
            action=action, user=actor, object_type="class_booking",
            object_id=str(booking.id), member_id=booking.member_id,
            after_state={
                "status": booking.status,
                "classSessionId": str(booking.class_session_id),
                "businessRef": str(booking.id),
            },
            reason=reason,
        )

    def _audit_session(
        self,
        action: str,
        session_id: UUID,
        actor: CurrentUser,
        trace_id: str,
        idempotency_key: str,
        target_status: str,
    ) -> None:
        record_audit(
            self.session, trace_id=trace_id, idempotency_key=idempotency_key,
            action=action, user=actor, object_type="class_session",
            object_id=str(session_id), after_state={"status": target_status},
        )

    @staticmethod
    def _utc(value: datetime | None) -> datetime:
        current = value or datetime.now(timezone.utc)
        if current.tzinfo is None or current.utcoffset() is None:
            raise HTTPException(status_code=422, detail="now must include timezone")
        return current.astimezone(timezone.utc)

    @staticmethod
    def _child_key(parent_key: str, booking_id: UUID) -> str:
        digest = hashlib.sha256(f"{parent_key}:{booking_id}".encode("utf-8")).hexdigest()
        return f"batch:{digest}"
