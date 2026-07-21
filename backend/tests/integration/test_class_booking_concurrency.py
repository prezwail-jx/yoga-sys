from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser
from app.domain import (
    AuditLog,
    CardProduct,
    ClassBooking,
    ClassSession,
    CoachProfile,
    Course,
    Member,
    MemberCard,
    Room,
    WriteOffEvent,
)
from app.repositories.class_booking import ClassBookingRepository
from app.repositories.class_session import ClassSessionRepository
from app.repositories.member import MemberRepository
from app.repositories.member_card_repository import MemberCardRepository
from app.repositories.writeoff_repository import WriteOffRepository
from app.services.class_booking import ClassBookingService
from app.services.writeoff_service import WriteOffService


NOW = datetime(2030, 1, 7, 9, 0, tzinfo=timezone.utc)
TODAY = date(2030, 1, 7)


@dataclass
class Scenario:
    course_id: UUID
    room_id: UUID
    coach_id: UUID
    session_id: UUID
    product_id: UUID
    member_ids: list[UUID]


def _service(session: Session) -> ClassBookingService:
    return ClassBookingService(
        session,
        ClassBookingRepository(session),
        ClassSessionRepository(session),
        WriteOffService(
            session,
            MemberRepository(session),
            MemberCardRepository(session),
            WriteOffRepository(session),
        ),
    )


@pytest.fixture
def committed_scenario(db_engine):
    scenarios: list[Scenario] = []

    def create(*, member_count: int, capacity: int = 1) -> Scenario:
        suffix = uuid4().hex[:10]
        course = Course(
            id=uuid4(), name=f"并发课程-{suffix}", duration_minutes=60,
            difficulty="all_levels", enabled=True,
        )
        room = Room(id=uuid4(), name=f"并发教室-{suffix}", capacity=capacity, enabled=True)
        coach = CoachProfile(id=uuid4(), name=f"并发教练-{suffix}", enabled=True)
        product = CardProduct(
            id=uuid4(), name=f"并发次卡-{suffix}", card_type="times",
            price=Decimal("300.00"), total_times=10, valid_days=90,
            activation_mode="immediate", applicable_course_scope="group",
            absence_deduct_enabled=True, cancel_refund_enabled=True, enabled=True,
        )
        class_session = ClassSession(
            id=uuid4(), course_id=course.id, room_id=room.id,
            coach_profile_id=coach.id, start_at=NOW + timedelta(hours=1),
            end_at=NOW + timedelta(hours=2), capacity=capacity,
            booking_open_hours_before=168, booking_close_minutes_before=0,
            cancel_cutoff_minutes_before=0, status="published", created_by="test",
        )
        members = [
            Member(
                id=uuid4(), name=f"并发会员-{suffix}-{index}",
                phone=f"139{int(suffix[:7], 16) % 10_000_000:07d}{index:02d}",
                join_date=TODAY, status="normal",
            )
            for index in range(member_count)
        ]
        cards = [
            MemberCard(
                id=uuid4(), member_id=member.id, card_product_id=product.id,
                status="active", product_name=product.name, card_type="times",
                terms_snapshot={
                    "activationMode": "immediate",
                    "applicableCourseScope": "group",
                    "absenceDeductEnabled": True,
                    "cancelRefundEnabled": True,
                },
                remaining_times=10, used_times=0, valid_days=90,
                opened_on=TODAY, expires_on=TODAY + timedelta(days=89),
            )
            for member in members
        ]
        scenario = Scenario(
            course.id, room.id, coach.id, class_session.id, product.id,
            [member.id for member in members],
        )
        with Session(db_engine) as session:
            session.add_all([course, room, coach, product])
            session.flush()
            session.add_all([class_session, *members])
            session.flush()
            session.add_all(cards)
            session.commit()
        scenarios.append(scenario)
        return scenario

    yield create

    with Session(db_engine) as session:
        for scenario in reversed(scenarios):
            booking_ids = list(session.scalars(
                select(ClassBooking.id).where(ClassBooking.class_session_id == scenario.session_id)
            ))
            session.execute(delete(AuditLog).where(AuditLog.member_id.in_(scenario.member_ids)))
            if booking_ids:
                session.execute(delete(WriteOffEvent).where(WriteOffEvent.business_ref.in_(map(str, booking_ids))))
            session.execute(delete(ClassBooking).where(ClassBooking.class_session_id == scenario.session_id))
            session.execute(delete(MemberCard).where(MemberCard.member_id.in_(scenario.member_ids)))
            session.execute(delete(ClassSession).where(ClassSession.id == scenario.session_id))
            session.execute(delete(Member).where(Member.id.in_(scenario.member_ids)))
            session.execute(delete(CardProduct).where(CardProduct.id == scenario.product_id))
            session.execute(delete(CoachProfile).where(CoachProfile.id == scenario.coach_id))
            session.execute(delete(Room).where(Room.id == scenario.room_id))
            session.execute(delete(Course).where(Course.id == scenario.course_id))
        session.commit()


def _book(db_engine, barrier: Barrier, scenario: Scenario, member_id: UUID, key: str):
    barrier.wait()
    with Session(db_engine) as session:
        try:
            result = _service(session).create(
                session_id=scenario.session_id, member_id=member_id,
                actor=CurrentUser(user_id="admin", role="admin"),
                idempotency_key=key, trace_id=key, now=NOW, today=TODAY,
            )
            session.commit()
            return 201, result["id"]
        except HTTPException as exc:
            session.rollback()
            return exc.status_code, exc.detail


@pytest.mark.integration
def test_last_seat_concurrency_allows_exactly_one_booking(db_engine, committed_scenario):
    scenario = committed_scenario(member_count=2, capacity=1)
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(
            lambda args: _book(db_engine, barrier, scenario, *args),
            [(scenario.member_ids[0], "last-seat-a"), (scenario.member_ids[1], "last-seat-b")],
        ))

    assert sorted(status for status, _ in results) == [201, 409]
    with Session(db_engine) as session:
        occupied = session.scalar(select(func.count()).select_from(ClassBooking).where(
            ClassBooking.class_session_id == scenario.session_id,
            ClassBooking.status == "reserved",
        ))
    assert occupied == 1


@pytest.mark.integration
def test_duplicate_booking_concurrency_creates_one_reservation_and_hold(db_engine, committed_scenario):
    scenario = committed_scenario(member_count=1, capacity=2)
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(
            lambda key: _book(db_engine, barrier, scenario, scenario.member_ids[0], key),
            ["duplicate-a", "duplicate-b"],
        ))

    assert sorted(status for status, _ in results) == [201, 409]
    with Session(db_engine) as session:
        bookings = list(session.scalars(select(ClassBooking).where(
            ClassBooking.class_session_id == scenario.session_id,
            ClassBooking.member_id == scenario.member_ids[0],
        )))
        holds = list(session.scalars(select(WriteOffEvent).where(
            WriteOffEvent.member_id == scenario.member_ids[0],
            WriteOffEvent.event_type == "reserve_hold",
        )))
    assert len(bookings) == 1
    assert len(holds) == 1


@pytest.mark.integration
def test_terminal_event_concurrency_allows_cancel_or_checkin_only(db_engine, committed_scenario):
    scenario = committed_scenario(member_count=1, capacity=1)
    booking_status, booking_id = _book(
        db_engine, Barrier(1), scenario, scenario.member_ids[0], "terminal-reserve"
    )
    assert booking_status == 201
    barrier = Barrier(2)

    def terminal(action: str):
        barrier.wait()
        with Session(db_engine) as session:
            service = _service(session)
            try:
                if action == "cancel":
                    result = service.cancel(
                        booking_id, actor=CurrentUser(user_id="admin", role="admin"),
                        idempotency_key="terminal-cancel", trace_id="terminal-cancel",
                        now=NOW + timedelta(minutes=45), today=TODAY,
                    )
                else:
                    result = service.check_in(
                        booking_id, actor=CurrentUser(user_id="admin", role="admin"),
                        idempotency_key="terminal-checkin", trace_id="terminal-checkin",
                        now=NOW + timedelta(minutes=45), today=TODAY,
                    )
                session.commit()
                return 200, result["status"]
            except HTTPException as exc:
                session.rollback()
                return exc.status_code, exc.detail

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(terminal, ["cancel", "checkin"]))

    assert sorted(status for status, _ in results) == [200, 409]
    with Session(db_engine) as session:
        booking = session.get(ClassBooking, booking_id)
        terminals = list(session.scalars(select(WriteOffEvent).where(
            WriteOffEvent.business_ref == str(booking_id),
            WriteOffEvent.event_type.in_(("cancel_refund", "checkin_commit", "absence_commit")),
        )))
    assert booking.status in {"cancelled", "checked_in"}
    assert len(terminals) == 1
