from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.class_booking import ClassBooking
from app.repositories.member_card_repository import MemberCardRepository
from app.services.class_booking import ClassBookingService
from app.services.writeoff_service import WriteOffService


NOW = datetime(2030, 1, 7, 9, 0, tzinfo=timezone.utc)


def _service():
    booking_repo = MagicMock()
    session_repo = MagicMock()
    writeoff = MagicMock()
    service = ClassBookingService(MagicMock(), booking_repo, session_repo, writeoff)
    return service, booking_repo, session_repo, writeoff


def _actor(role="admin", *, member_id=None, coach_profile_id=None):
    return SimpleNamespace(
        user_id=f"{role}-1",
        role=role,
        member_id=str(member_id) if member_id else None,
        coach_profile_id=str(coach_profile_id) if coach_profile_id else None,
    )


def _class_session(**changes):
    values = {
        "id": uuid4(),
        "course_id": uuid4(),
        "coach_profile_id": uuid4(),
        "start_at": NOW + timedelta(hours=1),
        "end_at": NOW + timedelta(hours=2),
        "capacity": 10,
        "booking_open_hours_before": 24,
        "booking_close_minutes_before": 0,
        "cancel_cutoff_minutes_before": 30,
        "status": "published",
    }
    values.update(changes)
    return SimpleNamespace(**values)


@patch("app.services.class_booking.record_audit")
def test_member_booking_uses_token_identity_and_booking_id_as_business_ref(_audit):
    service, booking_repo, session_repo, writeoff = _service()
    member_id = uuid4()
    other_member_id = uuid4()
    class_session = _class_session()
    booking_repo.lock_member.return_value = SimpleNamespace(status="normal")
    booking_repo.occupied_count.return_value = 0
    booking_repo.has_active_booking.return_value = False
    booking_repo.has_member_overlap.return_value = False

    def create(booking):
        booking.id = uuid4()
        return booking

    booking_repo.create.side_effect = create
    booking_repo.get_projected.side_effect = lambda booking_id: {"id": booking_id}
    session_repo.get_by_id.return_value = class_session

    actor = _actor("member", member_id=member_id)
    with pytest.raises(HTTPException) as forbidden:
        service.create(
            session_id=class_session.id, member_id=other_member_id, actor=actor,
            idempotency_key="booking-key", trace_id="trace-1", now=NOW,
        )
    assert forbidden.value.status_code == 403

    result = service.create(
        session_id=class_session.id, member_id=None, actor=actor,
        idempotency_key="booking-key", trace_id="trace-1", now=NOW,
    )

    booking_repo.lock_member.assert_called_once_with(member_id)
    created = booking_repo.create.call_args.args[0]
    assert created.member_id == member_id
    assert result["id"] == created.id
    writeoff.apply.assert_called_once_with(
        member_id=member_id,
        business_ref=str(created.id),
        event_type="reserve_hold",
        user=actor,
        idempotency_key="booking-key",
        trace_id="trace-1",
        today=NOW.date(),
        course_id=class_session.course_id,
    )


def test_member_booking_window_is_half_open_and_admin_bypasses_it():
    service, booking_repo, session_repo, _ = _service()
    member_id = uuid4()
    class_session = _class_session(
        start_at=NOW + timedelta(hours=2),
        booking_open_hours_before=1,
        booking_close_minutes_before=30,
    )
    booking_repo.lock_member.return_value = SimpleNamespace(status="normal")
    session_repo.get_by_id.return_value = class_session

    with pytest.raises(HTTPException, match="预约窗口"):
        service.create(
            session_id=class_session.id,
            actor=_actor("member", member_id=member_id),
            idempotency_key="key",
            trace_id="trace",
            now=NOW,
        )

    booking_repo.occupied_count.return_value = class_session.capacity
    with pytest.raises(HTTPException, match="满员"):
        service.create(
            session_id=class_session.id,
            member_id=member_id,
            actor=_actor("admin"),
            idempotency_key="key",
            trace_id="trace",
            now=NOW,
        )


@patch("app.services.class_booking.record_audit")
def test_member_cancel_cutoff_and_admin_override(_audit):
    service, booking_repo, session_repo, writeoff = _service()
    member_id = uuid4()
    class_session = _class_session(start_at=NOW + timedelta(hours=1))
    booking = ClassBooking(
        id=uuid4(), member_id=member_id, class_session_id=class_session.id,
        status="reserved", booked_by_id="member-1", booked_by_role="member",
        trace_id="trace",
    )
    booking_repo.get_by_id.return_value = booking
    booking_repo.get_projected.return_value = {"id": booking.id, "status": "cancelled"}
    session_repo.get_by_id.return_value = class_session

    with pytest.raises(HTTPException, match="取消截止"):
        service.cancel(
            booking.id, actor=_actor("member", member_id=member_id),
            idempotency_key="late-member-cancel", trace_id="trace",
            now=NOW + timedelta(minutes=31),
        )
    writeoff.apply.assert_not_called()

    admin = _actor("admin")
    result = service.cancel(
        booking.id, actor=admin, idempotency_key="admin-cancel",
        trace_id="trace", now=NOW + timedelta(minutes=31),
    )

    assert result["status"] == "cancelled"
    assert booking.status == "cancelled"
    writeoff.apply.assert_called_once_with(
        member_id=member_id, business_ref=str(booking.id), event_type="cancel_refund",
        user=admin,
        idempotency_key="admin-cancel", trace_id="trace", today=NOW.date(),
    )


@patch("app.services.class_booking.record_audit")
def test_assigned_coach_checkin_rejects_wrong_coach_and_terminal_booking(_audit):
    service, booking_repo, session_repo, writeoff = _service()
    coach_id = uuid4()
    class_session = _class_session(coach_profile_id=coach_id)
    booking = ClassBooking(
        id=uuid4(), member_id=uuid4(), class_session_id=class_session.id,
        status="reserved", booked_by_id="admin-1", booked_by_role="admin",
        trace_id="trace",
    )
    booking_repo.get_by_id.return_value = booking
    booking_repo.get_projected.return_value = {"id": booking.id, "status": "checked_in"}
    session_repo.get_by_id.return_value = class_session

    with pytest.raises(HTTPException, match="指定教练"):
        service.check_in(
            booking.id, actor=_actor("coach", coach_profile_id=uuid4()),
            idempotency_key="wrong-coach", trace_id="trace", now=NOW + timedelta(minutes=30),
        )

    actor = _actor("coach", coach_profile_id=coach_id)
    result = service.check_in(
        booking.id, actor=actor, idempotency_key="assigned-coach",
        trace_id="trace", now=NOW + timedelta(minutes=30),
    )
    assert result["status"] == "checked_in"
    assert booking.status == "checked_in"
    writeoff.apply.assert_called_once()

    with pytest.raises(HTTPException, match="已预约"):
        service.check_in(
            booking.id, actor=actor, idempotency_key="second-checkin",
            trace_id="trace", now=NOW + timedelta(minutes=31),
        )


@patch("app.services.class_booking.record_audit")
def test_venue_cancel_refuses_checked_in_before_force_refunds(_audit):
    service, booking_repo, session_repo, writeoff = _service()
    class_session = _class_session()
    session_repo.get_by_id.return_value = class_session
    booking_repo.list_for_session.return_value = [
        ClassBooking(id=uuid4(), member_id=uuid4(), class_session_id=class_session.id, status="reserved"),
        ClassBooking(id=uuid4(), member_id=uuid4(), class_session_id=class_session.id, status="checked_in"),
    ]

    with pytest.raises(HTTPException, match="已签到"):
        service.cancel_session(
            class_session.id,
            actor=_actor("admin"),
            idempotency_key="cancel-session",
            trace_id="trace",
            now=NOW,
        )

    writeoff.apply.assert_not_called()
    session_repo.update_status.assert_not_called()


@patch("app.services.class_booking.record_audit")
def test_completion_processes_only_reserved_in_repository_order(_audit):
    service, booking_repo, session_repo, writeoff = _service()
    class_session = _class_session(end_at=NOW - timedelta(minutes=1))
    session_repo.get_by_id.return_value = class_session
    session_repo.get_projected.return_value = {"status": "completed"}
    first = ClassBooking(id=uuid4(), member_id=uuid4(), class_session_id=class_session.id, status="reserved")
    checked_in = ClassBooking(id=uuid4(), member_id=uuid4(), class_session_id=class_session.id, status="checked_in")
    second = ClassBooking(id=uuid4(), member_id=uuid4(), class_session_id=class_session.id, status="reserved")
    booking_repo.list_for_session.return_value = [first, checked_in, second]
    actor = _actor("admin")

    result = service.complete_session(
        class_session.id,
        actor=actor,
        idempotency_key="complete-session",
        trace_id="trace",
        now=NOW,
    )

    assert result == {"status": "completed"}
    assert first.status == second.status == "absent"
    assert checked_in.status == "checked_in"
    assert writeoff.apply.call_args_list == [
        call(
            member_id=first.member_id, business_ref=str(first.id), event_type="absence_commit",
            user=actor, idempotency_key=service._child_key("complete-session", first.id),
            trace_id="trace", today=NOW.date(),
        ),
        call(
            member_id=second.member_id, business_ref=str(second.id), event_type="absence_commit",
            user=actor, idempotency_key=service._child_key("complete-session", second.id),
            trace_id="trace", today=NOW.date(),
        ),
    ]


def test_course_card_candidates_keep_fefo_order_and_filter_scope():
    db = MagicMock()
    course_id = uuid4()
    cards = [
        SimpleNamespace(terms_snapshot={"applicableCourseScope": "private"}),
        SimpleNamespace(terms_snapshot={"applicableCourseScope": "specific", "specificCourseIds": [str(course_id)]}),
        SimpleNamespace(terms_snapshot={"applicableCourseScope": "group"}),
        SimpleNamespace(terms_snapshot={"applicableCourseScope": "specific", "specificCourseIds": [str(uuid4())]}),
    ]
    db.scalars.return_value.all.return_value = cards

    result = MemberCardRepository(db).list_fefo_candidates(
        uuid4(), NOW.date(), course_id=course_id, include_pending=True, for_update=True
    )

    assert result == cards[1:3]


def test_private_card_candidates_filter_out_group_only_cards():
    db = MagicMock()
    cards = [
        SimpleNamespace(card_type="times", terms_snapshot={"applicableCourseScope": "group"}),
        SimpleNamespace(card_type="times", terms_snapshot={"applicableCourseScope": "private"}),
        SimpleNamespace(card_type="private", terms_snapshot={}),
    ]
    db.scalars.return_value.all.return_value = cards

    result = MemberCardRepository(db).list_fefo_candidates(
        uuid4(), NOW.date(), applicable_scope="private", include_pending=True, for_update=True
    )

    assert result == cards[1:]


def test_private_reservation_rejects_member_without_eligible_card():
    member_repo = MagicMock()
    card_repo = MagicMock()
    writeoff_repo = MagicMock()
    service = WriteOffService(MagicMock(), member_repo, card_repo, writeoff_repo)
    member_id = uuid4()
    member_repo.get_by_id.return_value = SimpleNamespace(status="normal")
    writeoff_repo.get_event.return_value = None
    card_repo.list_fefo_candidates.return_value = []

    with pytest.raises(HTTPException) as error:
        service.apply(
            member_id=member_id, business_ref=str(uuid4()), event_type="reserve_hold",
            user=_actor("coach"), idempotency_key="private-confirm", trace_id="trace",
            today=NOW.date(), applicable_scope="private",
        )

    assert error.value.status_code == 409
    assert error.value.detail == "没有符合条件的会员卡"


@patch("app.services.writeoff_service.record_audit")
def test_force_refund_overrides_non_refundable_card_terms(_audit):
    member_repo = MagicMock()
    card_repo = MagicMock()
    writeoff_repo = MagicMock()
    service = WriteOffService(MagicMock(), member_repo, card_repo, writeoff_repo)
    member_id = uuid4()
    card_id = uuid4()
    member_repo.get_by_id.return_value = SimpleNamespace(status="paused")
    writeoff_repo.get_event.return_value = None
    reserve = SimpleNamespace(
        id=uuid4(), member_id=member_id, member_card_id=card_id,
        selection_basis="FEFO",
    )
    writeoff_repo.get_reserve.return_value = reserve
    writeoff_repo.get_terminal.return_value = None
    card = SimpleNamespace(
        id=card_id, status="active", remaining_times=0, used_times=0,
        valid_days=30, opened_on=NOW.date(), expires_on=NOW.date(), remind_on=None,
        frozen_from=None, frozen_until=None, freeze_reason=None, total_frozen_days=0,
        terms_snapshot={"cancelRefundEnabled": False},
    )
    card_repo.get_by_id.return_value = card
    writeoff_repo.create.side_effect = lambda event: event
    actor = _actor("admin")

    event = service.apply(
        member_id=member_id, business_ref=str(uuid4()), event_type="cancel_refund",
        user=actor, idempotency_key="force-refund", trace_id="trace",
        today=NOW.date(), force_refund=True,
    )

    assert card.remaining_times == 1
    assert card.used_times == 0
    assert event.times_delta == 1
