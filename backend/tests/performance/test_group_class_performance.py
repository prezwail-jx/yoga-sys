import math
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from time import perf_counter
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, insert, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.api.deps.auth import CurrentUser
from app.domain import (
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
from app.domain.base import Base
from app.repositories.class_booking import ClassBookingRepository
from app.repositories.class_session import ClassSessionRepository
from app.repositories.member import MemberRepository
from app.repositories.member_card_repository import MemberCardRepository
from app.repositories.writeoff_repository import WriteOffRepository
from app.services.class_booking import ClassBookingService
from app.services.member_timeline_service import MemberTimelineService
from app.services.writeoff_service import WriteOffService


BASE_TIME = datetime(2035, 1, 8, 9, 0, tzinfo=timezone.utc)
TODAY = date(2035, 1, 8)


@dataclass(frozen=True)
class Profile:
    members: int
    sessions: int
    bookings: int
    samples: int


PROFILES = {
    "smoke": Profile(members=1_000, sessions=250, bookings=1_000, samples=20),
    "target": Profile(members=20_000, sessions=5_000, bookings=100_000, samples=100),
}


def _chunks(items, size=2_000):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def _p95(samples: list[float]) -> float:
    return sorted(samples)[math.ceil(len(samples) * 0.95) - 1]


def _booking_service(session: Session) -> ClassBookingService:
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


@pytest.fixture(scope="module")
def perf_engine():
    database_url = os.getenv("PERF_DATABASE_URL")
    if not database_url:
        pytest.skip("Set PERF_DATABASE_URL to run performance records")
    url = make_url(database_url)
    if url.database != "yoga_sys_perf":
        pytest.fail("PERF_DATABASE_URL must target the dedicated yoga_sys_perf database")

    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(database_url, pool_pre_ping=True)
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
    yield engine
    engine.dispose()
    if previous_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous_url


def _seed(session: Session, profile: Profile):
    course_id, room_id, coach_id, product_id = (uuid4() for _ in range(4))
    member_ids = [uuid4() for _ in range(profile.members)]
    card_ids = [uuid4() for _ in range(profile.members)]
    session_ids = [uuid4() for _ in range(profile.sessions)]

    session.execute(insert(Course), [{
        "id": course_id, "name": "性能团课", "duration_minutes": 60,
        "difficulty": "all_levels", "enabled": True,
    }])
    session.execute(insert(Room), [{
        "id": room_id, "name": "性能教室", "capacity": 500, "enabled": True,
    }])
    session.execute(insert(CoachProfile), [{
        "id": coach_id, "name": "性能教练", "enabled": True,
    }])
    session.execute(insert(CardProduct), [{
        "id": product_id, "name": "性能次卡", "card_type": "times",
        "price": Decimal("1000.00"), "total_times": 200, "valid_days": 3650,
        "activation_mode": "immediate", "applicable_course_scope": "group",
        "absence_deduct_enabled": True, "cancel_refund_enabled": True, "enabled": True,
    }])

    members = [{
        "id": member_id, "name": f"性能会员-{index:05d}", "phone": f"188{index:08d}",
        "join_date": TODAY, "status": "normal",
    } for index, member_id in enumerate(member_ids)]
    cards = [{
        "id": card_ids[index], "member_id": member_id, "card_product_id": product_id,
        "status": "active", "product_name": "性能次卡", "card_type": "times",
        "terms_snapshot": {
            "activationMode": "immediate", "applicableCourseScope": "group",
            "absenceDeductEnabled": True, "cancelRefundEnabled": True,
        },
        "remaining_times": 200, "used_times": 0, "valid_days": 3650,
        "opened_on": TODAY, "expires_on": TODAY + timedelta(days=3649),
        "total_frozen_days": 0,
    } for index, member_id in enumerate(member_ids)]
    sessions = [{
        "id": session_id, "course_id": course_id, "room_id": room_id,
        "coach_profile_id": coach_id, "start_at": BASE_TIME + timedelta(hours=index * 2),
        "end_at": BASE_TIME + timedelta(hours=index * 2 + 1), "capacity": 500,
        "booking_open_hours_before": 8760, "booking_close_minutes_before": 0,
        "cancel_cutoff_minutes_before": 0, "status": "published", "created_by": "perf",
    } for index, session_id in enumerate(session_ids)]
    for rows, model in ((members, Member), (cards, MemberCard), (sessions, ClassSession)):
        for chunk in _chunks(rows):
            session.execute(insert(model), chunk)

    baseline_member_count = profile.members - profile.samples
    timeline_booking_ids: list[UUID] = []
    booking_rows = []
    for index in range(profile.bookings):
        booking_id = uuid4()
        member_index = 0 if index < 100 else 1 + ((index - 100) % (baseline_member_count - 1))
        booking_rows.append({
            "id": booking_id, "class_session_id": session_ids[index % (profile.sessions - 1)],
            "member_id": member_ids[member_index], "status": "cancelled",
            "booked_by_id": "perf", "booked_by_role": "admin",
            "terminal_by_id": "perf", "terminal_by_role": "admin", "terminal_at": BASE_TIME,
            "cancellation_reason": "performance fixture", "trace_id": f"seed-{index}",
        })
        if index < 100:
            timeline_booking_ids.append(booking_id)
        if len(booking_rows) == 2_000:
            session.execute(insert(ClassBooking), booking_rows)
            booking_rows.clear()
    if booking_rows:
        session.execute(insert(ClassBooking), booking_rows)

    timeline_events = [{
        "id": uuid4(), "member_id": member_ids[0], "member_card_id": card_ids[0],
        "event_type": "reserve_hold", "business_ref": str(booking_id), "sequence_no": 1,
        "times_delta": -1, "selection_basis": "performance fixture",
        "idempotency_key": f"timeline-{index}", "trace_id": f"timeline-{index}",
        "operator_id": "perf", "operator_role": "admin",
        "occurred_at": BASE_TIME + timedelta(seconds=index),
    } for index, booking_id in enumerate(timeline_booking_ids)]
    session.execute(insert(WriteOffEvent), timeline_events)
    session.commit()
    return member_ids, session_ids


@pytest.mark.performance
def test_group_class_target_volume_and_p95_records(perf_engine):
    profile_name = os.getenv("PERF_PROFILE", "smoke")
    if profile_name not in PROFILES:
        pytest.fail(f"PERF_PROFILE must be one of: {', '.join(PROFILES)}")
    profile = PROFILES[profile_name]

    with Session(perf_engine, expire_on_commit=False) as session:
        member_ids, session_ids = _seed(session, profile)
        assert session.scalar(select(func.count()).select_from(Member)) == profile.members
        assert session.scalar(select(func.count()).select_from(ClassSession)) == profile.sessions
        assert session.scalar(select(func.count()).select_from(ClassBooking)) == profile.bookings

        actor = CurrentUser(user_id="perf", role="admin")
        write_samples = []
        for index, member_id in enumerate(member_ids[-profile.samples:]):
            started = perf_counter()
            _booking_service(session).create(
                session_id=session_ids[-1], member_id=member_id, actor=actor,
                idempotency_key=f"perf-write-{index}", trace_id=f"perf-write-{index}",
                now=BASE_TIME - timedelta(days=1), today=TODAY,
            )
            session.commit()
            write_samples.append((perf_counter() - started) * 1000)

        timeline_samples = []
        for _ in range(profile.samples):
            started = perf_counter()
            items, total = MemberTimelineService(session).query(
                member_id=member_ids[0], actor_role="admin", limit=50,
            )
            timeline_samples.append((perf_counter() - started) * 1000)
            assert len(items) == 50
            assert total >= 100

    print(
        f"profile={profile_name} members={profile.members} sessions={profile.sessions} "
        f"bookings={profile.bookings} write_p95_ms={_p95(write_samples):.2f} "
        f"timeline_p95_ms={_p95(timeline_samples):.2f}"
    )
