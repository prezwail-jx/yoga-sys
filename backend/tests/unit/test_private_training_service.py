from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.private_training import PrivateTrainingService


NOW = datetime(2030, 1, 7, 9, 0, tzinfo=timezone.utc)


def _actor(role="admin", *, member_id=None, coach_profile_id=None):
    return SimpleNamespace(
        user_id=f"{role}-1",
        role=role,
        member_id=str(member_id) if member_id else None,
        coach_profile_id=str(coach_profile_id) if coach_profile_id else None,
    )


def _service():
    repo = MagicMock()
    member_repo = MagicMock()
    coach_repo = MagicMock()
    writeoff = MagicMock()
    service = PrivateTrainingService(MagicMock(), repo, member_repo, coach_repo, writeoff)
    return service, repo, member_repo, coach_repo, writeoff


def _slot(**changes):
    values = {
        "id": uuid4(),
        "coach_profile_id": uuid4(),
        "start_at": NOW,
        "end_at": NOW.replace(hour=10),
        "duration_minutes": 60,
        "status": "locked",
    }
    values.update(changes)
    return SimpleNamespace(**values)


def _booking(**changes):
    values = {
        "id": uuid4(),
        "availability_id": uuid4(),
        "member_id": uuid4(),
        "coach_profile_id": uuid4(),
        "member_card_id": None,
        "status": "pending",
        "member_message": None,
        "rejection_reason": None,
        "cancellation_reason": None,
        "confirmed_at": None,
        "terminal_by_id": None,
        "terminal_by_role": None,
        "terminal_at": None,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def _projection(booking, slot, **changes):
    value = {
        "id": booking.id,
        "availability_id": slot.id,
        "member_id": booking.member_id,
        "member_name": "会员",
        "coach_profile_id": booking.coach_profile_id,
        "coach_name": "教练",
        "member_card_id": booking.member_card_id,
        "start_at": slot.start_at,
        "end_at": slot.end_at,
        "duration_minutes": slot.duration_minutes,
        "status": booking.status,
        "member_message": booking.member_message,
        "rejection_reason": booking.rejection_reason,
        "cancellation_reason": booking.cancellation_reason,
        "booked_by_id": "member-1",
        "booked_by_role": "member",
        "confirmed_at": booking.confirmed_at,
        "terminal_by_id": booking.terminal_by_id,
        "terminal_by_role": booking.terminal_by_role,
        "terminal_at": booking.terminal_at,
        "trace_id": "trace",
        "created_at": NOW,
        "updated_at": NOW,
    }
    value.update(changes)
    return value


@patch("app.services.private_training.record_audit")
def test_confirm_private_booking_consumes_one_private_entitlement(_audit):
    service, repo, _, _, writeoff = _service()
    coach_id = uuid4()
    card_id = uuid4()
    slot = _slot(coach_profile_id=coach_id)
    booking = _booking(availability_id=slot.id, coach_profile_id=coach_id)
    repo.get_booking.return_value = booking
    repo.get_slot.return_value = slot
    repo.get_projected_booking.side_effect = lambda _id: _projection(booking, slot)
    writeoff.apply.return_value = SimpleNamespace(member_card_id=card_id)

    result = service.confirm_booking(
        booking.id,
        actor=_actor("coach", coach_profile_id=coach_id),
        idempotency_key="confirm-key",
        trace_id="trace",
        now=NOW,
        today=NOW.date(),
    )

    assert result["status"] == "confirmed"
    assert booking.member_card_id == card_id
    writeoff.apply.assert_called_once_with(
        member_id=booking.member_id,
        business_ref=str(booking.id),
        event_type="reserve_hold",
        user=writeoff.apply.call_args.kwargs["user"],
        idempotency_key="confirm-key",
        trace_id="trace",
        today=NOW.date(),
        applicable_scope="private",
    )


@patch("app.services.private_training.record_audit")
def test_member_can_cancel_pending_booking_without_writeoff(_audit):
    service, repo, _, _, writeoff = _service()
    member_id = uuid4()
    slot = _slot(status="locked")
    booking = _booking(availability_id=slot.id, member_id=member_id)
    repo.get_booking.return_value = booking
    repo.get_slot.return_value = slot
    repo.get_projected_booking.side_effect = lambda _id: _projection(booking, slot)

    result = service.cancel_pending_booking(
        booking.id,
        actor=_actor("member", member_id=member_id),
        reason="临时有事",
        trace_id="trace",
        now=NOW,
    )

    assert result["status"] == "cancelled"
    assert slot.status == "available"
    assert booking.cancellation_reason == "临时有事"
    writeoff.apply.assert_not_called()


@patch("app.services.private_training.record_audit")
def test_sign_in_requires_confirmed_booking_and_records_lesson(_audit):
    service, repo, _, _, writeoff = _service()
    coach_id = uuid4()
    slot = _slot(coach_profile_id=coach_id)
    booking = _booking(availability_id=slot.id, coach_profile_id=coach_id, status="confirmed")
    repo.get_booking.return_value = booking
    repo.get_slot.return_value = slot
    repo.get_projected_booking.side_effect = lambda _id: _projection(booking, slot)
    repo.create_lesson_record.side_effect = lambda record: record
    payload = SimpleNamespace(content="核心训练", consumed_hours=Decimal("1.5"), member_status_notes="状态良好")

    result = service.sign_in_booking(
        booking.id,
        payload,
        actor=_actor("admin"),
        idempotency_key="sign-key",
        trace_id="trace",
        now=NOW,
        today=NOW.date(),
    )

    assert result["status"] == "completed"
    assert booking.status == "completed"
    created = repo.create_lesson_record.call_args.args[0]
    assert created.content == "核心训练"
    assert created.consumed_hours == Decimal("1.5")
    writeoff.apply.assert_called_once_with(
        member_id=booking.member_id,
        business_ref=str(booking.id),
        event_type="checkin_commit",
        user=writeoff.apply.call_args.kwargs["user"],
        idempotency_key="sign-key",
        trace_id="trace",
        today=NOW.date(),
    )


def test_sign_in_rejects_unconfirmed_booking():
    service, repo, _, _, _ = _service()
    slot = _slot()
    booking = _booking(availability_id=slot.id, coach_profile_id=slot.coach_profile_id, status="pending")
    repo.get_booking.return_value = booking
    repo.get_slot.return_value = slot

    with pytest.raises(HTTPException) as error:
        service.sign_in_booking(
            booking.id,
            SimpleNamespace(content="内容", consumed_hours=Decimal("1"), member_status_notes=None),
            actor=_actor("admin"),
            idempotency_key="sign-key",
            trace_id="trace",
            now=NOW,
            today=NOW.date(),
        )

    assert error.value.status_code == 409
