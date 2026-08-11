from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.api.deps.business_clock import get_business_now
from app.domain import AuditLog
from app.main import app


SHANGHAI = ZoneInfo("Asia/Shanghai")
WEEK_START = date(2030, 1, 7)
NOW = datetime(2030, 1, 9, 12, 0, tzinfo=SHANGHAI)


def _key(headers: dict[str, str], value: str) -> dict[str, str]:
    return {**headers, "Idempotency-Key": value}


def _login(client, username: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": "secure123"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _coach(client, admin_headers, suffix: str):
    coach = client.post(
        "/coaches",
        json={"name": f"小程序教练{suffix}"},
        headers=admin_headers,
    )
    assert coach.status_code == 201, coach.text
    username = f"mini.coach.{suffix}"
    account = client.post(
        f"/coaches/{coach.json()['id']}/account",
        json={"username": username, "initialPassword": "secure123"},
        headers=_key(admin_headers, f"bind-mini-coach-{suffix}"),
    )
    assert account.status_code == 201, account.text
    return coach.json(), _login(client, username)


def _member(client, admin_headers, suffix: str) -> dict[str, str]:
    member = client.post(
        "/members",
        json={
            "name": f"小程序会员{suffix}",
            "phone": f"1388000{int(suffix):04d}",
            "joinDate": "2030-01-01",
        },
        headers=admin_headers,
    )
    assert member.status_code == 201, member.text
    username = f"mini.member.{suffix}"
    account = client.post(
        f"/members/{member.json()['id']}/account",
        json={"username": username, "initialPassword": "secure123"},
        headers=_key(admin_headers, f"bind-mini-member-{suffix}"),
    )
    assert account.status_code == 201, account.text
    return _login(client, username)


def _class_resources(client, admin_headers):
    course = client.post(
        "/courses",
        json={"name": "教练小程序隔离课程", "durationMinutes": 60},
        headers=admin_headers,
    )
    room = client.post(
        "/rooms",
        json={"name": "教练小程序隔离教室", "capacity": 10},
        headers=admin_headers,
    )
    assert course.status_code == room.status_code == 201
    return course.json(), room.json()


def _class_session(client, admin_headers, course, room, coach, start_at):
    response = client.post(
        "/class-sessions",
        json={
            "courseId": course["id"],
            "coachProfileId": coach["id"],
            "roomId": room["id"],
            "startAt": start_at.isoformat(),
            "endAt": (start_at + timedelta(hours=1)).isoformat(),
            "capacity": 10,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    published = client.post(f"/class-sessions/{response.json()['id']}/publish", headers=admin_headers)
    assert published.status_code == 200, published.text
    return published.json()


def test_assigned_schedule_and_cross_coach_roster_are_isolated_and_audited(
    client, db, auth_headers,
):
    owner, owner_headers = _coach(client, auth_headers, "7101")
    other, other_headers = _coach(client, auth_headers, "7102")
    course, room = _class_resources(client, auth_headers)
    owned = _class_session(
        client, auth_headers, course, room, owner,
        datetime(2030, 1, 8, 9, 0, tzinfo=SHANGHAI),
    )
    foreign = _class_session(
        client, auth_headers, course, room, other,
        datetime(2030, 1, 8, 11, 0, tzinfo=SHANGHAI),
    )

    schedule = client.get(
        "/class-sessions",
        params={"weekStart": WEEK_START.isoformat()},
        headers=owner_headers,
    )
    assert schedule.status_code == 200, schedule.text
    assert [item["id"] for item in schedule.json()["items"]] == [owned["id"]]

    denied = client.get(f"/class-sessions/{foreign['id']}/bookings", headers=owner_headers)
    assert denied.status_code == 403
    db.expire_all()
    audit = db.scalars(
        select(AuditLog).where(
            AuditLog.action == "get_class-sessions",
            AuditLog.object_id == foreign["id"],
            AuditLog.operator_role == "coach",
            AuditLog.result == "rejected",
        )
    ).first()
    assert audit is not None
    assert audit.reason == "Forbidden"


def test_cross_coach_private_booking_access_is_rejected_and_audited(client, db, auth_headers):
    app.dependency_overrides[get_business_now] = lambda: NOW
    owner, owner_headers = _coach(client, auth_headers, "7103")
    _, other_headers = _coach(client, auth_headers, "7104")
    member_headers = _member(client, auth_headers, "7103")
    start_at = datetime(2030, 1, 10, 9, 0, tzinfo=SHANGHAI)
    slot = client.post(
        "/private-slots",
        json={"startAt": start_at.isoformat(), "endAt": (start_at + timedelta(hours=1)).isoformat()},
        headers=_key(owner_headers, "coach-private-slot-7103"),
    )
    assert slot.status_code == 201, slot.text
    assert slot.json()["coachProfileId"] == owner["id"]
    booking = client.post(
        "/private-bookings",
        json={"availabilityId": slot.json()["id"], "memberMessage": "肩颈训练"},
        headers=_key(member_headers, "member-private-booking-7103"),
    )
    assert booking.status_code == 201, booking.text

    denied = client.get(f"/private-bookings/{booking.json()['id']}", headers=other_headers)
    assert denied.status_code == 403
    db.expire_all()
    audit = db.scalars(
        select(AuditLog).where(
            AuditLog.action == "get_private-bookings",
            AuditLog.object_id == booking.json()["id"],
            AuditLog.operator_role == "coach",
            AuditLog.result == "rejected",
        )
    ).first()
    assert audit is not None
    assert audit.reason == "Forbidden"
