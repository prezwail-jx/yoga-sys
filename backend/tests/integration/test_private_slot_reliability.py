from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.api.deps.business_clock import get_business_now
from app.main import app


SHANGHAI = ZoneInfo("Asia/Shanghai")
NOW = datetime(2030, 1, 9, 12, 0, tzinfo=SHANGHAI)


def _at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2030, 1, day, hour, minute, tzinfo=SHANGHAI)


def _headers(client, username: str, password: str = "secure123") -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _key(headers: dict[str, str], value: str) -> dict[str, str]:
    return {**headers, "Idempotency-Key": value}


def _coach(client, admin_headers, suffix: str, *, enabled: bool = True):
    response = client.post(
        "/coaches",
        json={"name": f"可靠性教练{suffix}", "enabled": enabled},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    coach = response.json()
    if not enabled:
        return coach, None
    username = f"slot.coach.{suffix}"
    account = client.post(
        f"/coaches/{coach['id']}/account",
        json={"username": username, "initialPassword": "secure123"},
        headers=_key(admin_headers, f"bind-slot-coach-{suffix}"),
    )
    assert account.status_code == 201, account.text
    return coach, _headers(client, username)


def _member_headers(client, admin_headers, suffix: str) -> dict[str, str]:
    member = client.post(
        "/members",
        json={
            "name": f"可靠性会员{suffix}",
            "phone": f"1399000{int(suffix):04d}",
            "joinDate": "2030-01-01",
        },
        headers=admin_headers,
    )
    assert member.status_code == 201, member.text
    username = f"slot.member.{suffix}"
    account = client.post(
        f"/members/{member.json()['id']}/account",
        json={"username": username, "initialPassword": "secure123"},
        headers=_key(admin_headers, f"bind-slot-member-{suffix}"),
    )
    assert account.status_code == 201, account.text
    return _headers(client, username)


def _slot(client, headers, start_at: datetime, *, coach_id: str | None = None, key: str | None = None):
    payload = {
        "startAt": start_at.isoformat(),
        "endAt": (start_at + timedelta(hours=1)).isoformat(),
    }
    if coach_id:
        payload["coachProfileId"] = coach_id
    request_headers = _key(headers, key) if key else headers
    return client.post("/private-slots", json=payload, headers=request_headers)


def test_single_slot_mutations_replay_and_browser_calls_without_keys(client, auth_headers):
    app.dependency_overrides[get_business_now] = lambda: NOW
    coach, coach_headers = _coach(client, auth_headers, "6201")

    browser_create = _slot(client, coach_headers, _at(10, 9))
    assert browser_create.status_code == 201, browser_create.text

    created = _slot(client, coach_headers, _at(11, 9), key="slot-create-6201")
    replayed_create = _slot(client, coach_headers, _at(11, 9), key="slot-create-6201")
    assert created.status_code == replayed_create.status_code == 201
    assert replayed_create.json() == created.json()
    changed_create = _slot(client, coach_headers, _at(12, 9), key="slot-create-6201")
    assert changed_create.status_code == 409

    slot_id = created.json()["id"]
    update_payload = {
        "startAt": _at(11, 10).isoformat(),
        "endAt": _at(11, 11).isoformat(),
    }
    updated = client.patch(
        f"/private-slots/{slot_id}",
        json=update_payload,
        headers=_key(coach_headers, "slot-update-6201"),
    )
    replayed_update = client.patch(
        f"/private-slots/{slot_id}",
        json=update_payload,
        headers=_key(coach_headers, "slot-update-6201"),
    )
    assert updated.status_code == replayed_update.status_code == 200
    assert replayed_update.json() == updated.json()
    changed_update = client.patch(
        f"/private-slots/{slot_id}",
        json={"startAt": _at(11, 11).isoformat(), "endAt": _at(11, 12).isoformat()},
        headers=_key(coach_headers, "slot-update-6201"),
    )
    assert changed_update.status_code == 409

    cancelled = client.delete(
        f"/private-slots/{slot_id}", headers=_key(coach_headers, "slot-cancel-6201")
    )
    replayed_cancel = client.delete(
        f"/private-slots/{slot_id}", headers=_key(coach_headers, "slot-cancel-6201")
    )
    assert cancelled.status_code == replayed_cancel.status_code == 200
    assert replayed_cancel.json() == cancelled.json()

    browser_cancel = client.delete(
        f"/private-slots/{browser_create.json()['id']}", headers=coach_headers
    )
    assert browser_cancel.status_code == 200
    assert browser_cancel.json()["status"] == "cancelled"
    assert coach["id"] == created.json()["coachProfileId"]


def test_cross_coach_mutations_are_rejected_with_or_without_retry_keys(client, auth_headers):
    app.dependency_overrides[get_business_now] = lambda: NOW
    owner, owner_headers = _coach(client, auth_headers, "6202")
    _, other_headers = _coach(client, auth_headers, "6203")
    owned = _slot(client, owner_headers, _at(10, 13))
    assert owned.status_code == 201, owned.text
    slot_id = owned.json()["id"]

    foreign_create = _slot(
        client, other_headers, _at(10, 15), coach_id=owner["id"], key="foreign-create-6203"
    )
    assert foreign_create.status_code == 403
    foreign_update = client.patch(
        f"/private-slots/{slot_id}",
        json={"startAt": _at(10, 14).isoformat(), "endAt": _at(10, 15).isoformat()},
        headers=_key(other_headers, "foreign-update-6203"),
    )
    assert foreign_update.status_code == 403
    foreign_cancel = client.delete(
        f"/private-slots/{slot_id}", headers=_key(other_headers, "foreign-cancel-6203")
    )
    assert foreign_cancel.status_code == 403

    visible = client.get("/private-slots", headers=owner_headers)
    assert visible.status_code == 200
    assert next(item for item in visible.json()["items"] if item["id"] == slot_id)["status"] == "available"


def test_locked_slot_cancellation_preserves_active_booking(client, auth_headers):
    app.dependency_overrides[get_business_now] = lambda: NOW
    _, coach_headers = _coach(client, auth_headers, "6204")
    member_headers = _member_headers(client, auth_headers, "6204")
    created = _slot(client, coach_headers, _at(12, 9))
    assert created.status_code == 201, created.text

    booking = client.post(
        "/private-bookings",
        json={"availabilityId": created.json()["id"], "memberMessage": "网络重试验收"},
        headers=_key(member_headers, "private-booking-6204"),
    )
    assert booking.status_code == 201, booking.text
    assert booking.json()["status"] == "pending"

    cancel = client.delete(
        f"/private-slots/{created.json()['id']}",
        headers=_key(coach_headers, "locked-cancel-6204"),
    )
    assert cancel.status_code == 409
    assert cancel.json()["detail"] == "该时段存在有效预约"
    listed = client.get("/private-slots", headers=coach_headers).json()["items"]
    assert next(item for item in listed if item["id"] == created.json()["id"])["status"] == "locked"


def test_private_slot_schedule_and_enabled_coach_rules(client, auth_headers):
    app.dependency_overrides[get_business_now] = lambda: NOW
    coach, coach_headers = _coach(client, auth_headers, "6205")
    base = _slot(client, coach_headers, _at(10, 9))
    assert base.status_code == 201, base.text
    overlap = _slot(client, coach_headers, _at(10, 9, 30))
    assert overlap.status_code == 409
    assert overlap.json()["detail"] == "private_slot_time_conflict"

    course = client.post(
        "/courses", json={"name": "可靠性课程6205", "durationMinutes": 60}, headers=auth_headers
    )
    room = client.post(
        "/rooms", json={"name": "可靠性教室6205", "capacity": 10}, headers=auth_headers
    )
    assert course.status_code == room.status_code == 201
    class_session = client.post(
        "/class-sessions",
        json={
            "courseId": course.json()["id"],
            "coachProfileId": coach["id"],
            "roomId": room.json()["id"],
            "startAt": _at(11, 9).isoformat(),
            "endAt": _at(11, 10).isoformat(),
            "capacity": 10,
        },
        headers=auth_headers,
    )
    assert class_session.status_code == 201, class_session.text
    class_overlap = _slot(client, coach_headers, _at(11, 9, 30))
    assert class_overlap.status_code == 409
    assert class_overlap.json()["detail"] == "coach_class_time_conflict"

    disabled, _ = _coach(client, auth_headers, "6206", enabled=False)
    disabled_create = _slot(client, auth_headers, _at(12, 13), coach_id=disabled["id"])
    assert disabled_create.status_code == 404
    assert disabled_create.json()["detail"] == "未找到启用的教练"


def test_future_time_and_week_generation_replay_with_explicit_conflicts(client, auth_headers):
    app.dependency_overrides[get_business_now] = lambda: NOW
    coach, coach_headers = _coach(client, auth_headers, "6207")

    past_create = _slot(client, coach_headers, _at(8, 9))
    assert past_create.status_code == 409
    assert past_create.json()["detail"] == "私教时段已开始或已结束"
    future = _slot(client, coach_headers, _at(12, 13))
    assert future.status_code == 201, future.text
    past_update = client.patch(
        f"/private-slots/{future.json()['id']}",
        json={"startAt": _at(8, 13).isoformat(), "endAt": _at(8, 14).isoformat()},
        headers=coach_headers,
    )
    assert past_update.status_code == 409
    assert past_update.json()["detail"] == "私教时段已开始或已结束"

    existing = _slot(client, coach_headers, _at(11, 9, 30))
    assert existing.status_code == 201, existing.text
    payload = {
        "weekStart": _at(7, 0).isoformat(),
        "weekdays": [0, 4, 5],
        "startTime": "09:00",
        "durationMinutes": 60,
    }
    missing_key = client.post(
        "/private-slots/generate-week", json=payload, headers=coach_headers
    )
    assert missing_key.status_code == 422
    generated = client.post(
        "/private-slots/generate-week",
        json=payload,
        headers=_key(coach_headers, "generate-week-6207"),
    )
    replayed = client.post(
        "/private-slots/generate-week",
        json=payload,
        headers=_key(coach_headers, "generate-week-6207"),
    )
    assert generated.status_code == replayed.status_code == 200
    assert replayed.json() == generated.json()
    assert len(generated.json()["created"]) == 1
    assert {item["reason"] for item in generated.json()["conflicts"]} == {
        "private_slot_in_past",
        "private_slot_time_conflict",
    }

    disabled = client.patch(
        f"/coaches/{coach['id']}", json={"enabled": False}, headers=auth_headers
    )
    assert disabled.status_code == 200
    disabled_update = client.patch(
        f"/private-slots/{future.json()['id']}",
        json={"startAt": _at(12, 14).isoformat(), "endAt": _at(12, 15).isoformat()},
        headers=coach_headers,
    )
    assert disabled_update.status_code == 404
    assert disabled_update.json()["detail"] == "未找到启用的教练"
