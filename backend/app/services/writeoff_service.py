from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException

from app.api.audit import record_audit
from app.domain.writeoff_event import TERMINAL_EVENT_TYPES, WriteOffEvent
from app.repositories.member import MemberRepository
from app.repositories.member_card_repository import MemberCardRepository
from app.repositories.writeoff_repository import WriteOffRepository
from app.services.transaction_service import card_state

if TYPE_CHECKING:
    from app.api.deps.auth import CurrentUser

class WriteOffService:
    def __init__(self, session, member_repo: MemberRepository, card_repo: MemberCardRepository, writeoff_repo: WriteOffRepository):
        self.session = session
        self.member_repo = member_repo
        self.card_repo = card_repo
        self.writeoff_repo = writeoff_repo

    def apply(
        self,
        *,
        member_id: UUID,
        business_ref: str,
        event_type: str,
        user: CurrentUser,
        idempotency_key: str,
        trace_id: str,
        today: date,
        course_id: UUID | None = None,
        force_refund: bool = False,
    ) -> WriteOffEvent:
        self.writeoff_repo.lock_chain(business_ref)
        existing = self.writeoff_repo.get_event(business_ref, event_type)
        if existing:
            if existing.member_id != member_id:
                raise HTTPException(status_code=409, detail="Business reference belongs to another member")
            return existing
        member = self.member_repo.get_by_id(member_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        if event_type == "reserve_hold" and member.status != "normal":
            raise HTTPException(status_code=409, detail="Member status does not allow write-off")
        if event_type == "reserve_hold":
            return self._reserve(member_id, business_ref, user, idempotency_key, trace_id, today, course_id)
        if event_type not in TERMINAL_EVENT_TYPES:
            raise HTTPException(status_code=422, detail="Unsupported write-off event")
        return self._terminal(
            member_id, business_ref, event_type, user, idempotency_key, trace_id,
            force_refund=force_refund,
        )

    def _reserve(self, member_id, business_ref, user, key, trace_id, today, course_id):
        cards = self.card_repo.list_fefo_candidates(
            member_id, today, for_update=True, include_pending=True, course_id=course_id
        )
        cards = [
            card for card in cards
            if card.status != "pending_activation"
            or (card.terms_snapshot or {}).get("activationMode") == "first_booking"
        ]
        if not cards:
            raise HTTPException(status_code=409, detail="No eligible member card")
        card = cards[0]
        before = card_state(card)
        if card.status == "pending_activation":
            card.status = "active"
            card.opened_on = today
            if card.valid_days:
                card.expires_on = today + timedelta(days=card.valid_days - 1)
                card.remind_on = card.expires_on - timedelta(days=7)
        times_delta = 0
        if card.remaining_times is not None:
            if card.remaining_times <= 0:
                raise HTTPException(status_code=409, detail="Member card has no remaining times")
            card.remaining_times -= 1
            times_delta = -1
        self.card_repo.update(card)
        basis = f"FEFO expires={card.expires_on or 'none'}, opened={card.opened_on or 'none'}, card={card.id}"
        if course_id is not None:
            basis += f", course={course_id}"
        event = self.writeoff_repo.create(WriteOffEvent(
            member_id=member_id, member_card_id=card.id, event_type="reserve_hold",
            business_ref=business_ref, sequence_no=1, times_delta=times_delta,
            selection_basis=basis, idempotency_key=key, trace_id=trace_id,
            operator_id=user.user_id, operator_role=user.role,
        ))
        self._audit(event, card, user, before, trace_id, key)
        return event

    def _terminal(self, member_id, business_ref, event_type, user, key, trace_id, *, force_refund=False):
        reserve = self.writeoff_repo.get_reserve(business_ref, for_update=True)
        if not reserve or reserve.member_id != member_id:
            raise HTTPException(status_code=409, detail="reserve_hold must exist before terminal event")
        terminal = self.writeoff_repo.get_terminal(business_ref)
        if terminal:
            raise HTTPException(status_code=409, detail="Write-off chain already has a terminal event")
        card = self.card_repo.get_by_id(reserve.member_card_id, for_update=True)
        if not card:
            raise HTTPException(status_code=404, detail="Member card not found")
        before = card_state(card)
        terms = card.terms_snapshot or {}
        times_delta = 0
        consume = event_type == "checkin_commit"
        if event_type == "cancel_refund" and force_refund:
            consume = False
        elif event_type == "cancel_refund":
            consume = not bool(terms.get("cancelRefundEnabled", False))
        elif event_type == "absence_commit":
            consume = bool(terms.get("absenceDeductEnabled", False))
        if card.remaining_times is not None:
            if consume:
                card.used_times += 1
            else:
                card.remaining_times += 1
                times_delta = 1
        elif consume:
            card.used_times += 1
        self.card_repo.update(card)
        event = self.writeoff_repo.create(WriteOffEvent(
            member_id=member_id, member_card_id=card.id, previous_event_id=reserve.id,
            event_type=event_type, business_ref=business_ref, sequence_no=2,
            times_delta=times_delta, selection_basis=reserve.selection_basis,
            idempotency_key=key, trace_id=trace_id,
            operator_id=user.user_id, operator_role=user.role,
        ))
        self._audit(
            event, card, user, before, trace_id, key,
            reason="venue_cancel_force_refund" if event_type == "cancel_refund" and force_refund else None,
        )
        return event

    def _audit(self, event, card, user, before, trace_id, key, reason=None):
        record_audit(
            self.session, trace_id=trace_id, idempotency_key=key, action=event.event_type,
            user=user, object_type="writeoff_event", object_id=str(event.id),
            member_id=event.member_id, before_state=before, after_state=card_state(card),
            reason=reason,
        )
