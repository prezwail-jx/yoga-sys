from datetime import date, datetime, timedelta, timezone
from uuid import uuid4


SOURCE_WEEK = date(2030, 1, 7)
TARGET_WEEK = date(2030, 1, 14)


def _course(client, headers, name="流瑜伽"):
    response = client.post(
        "/courses",
        json={"name": name, "durationMinutes": 60, "difficulty": "all_levels"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _room(client, headers, name="一号教室", capacity=20):
    response = client.post("/rooms", json={"name": name, "capacity": capacity}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _coach(client, headers, course_id, name="李教练"):
    response = client.post(
        "/coaches",
        json={"name": name, "specialtyCourseIds": [course_id]},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _session(client, headers, course, room, coach, start, capacity=12):
    response = client.post(
        "/class-sessions",
        json={
            "courseId": course["id"], "roomId": room["id"],
            "coachProfileId": coach["id"], "startAt": start.isoformat(),
            "endAt": (start + timedelta(hours=1)).isoformat(), "capacity": capacity,
        },
        headers=headers,
    )
    return response


def test_catalog_permissions_and_case_insensitive_uniqueness(client, auth_headers, coach_headers):
    course = _course(client, auth_headers)
    assert client.get("/courses", headers=coach_headers).status_code == 200
    forbidden = client.post(
        "/rooms", json={"name": "越权教室", "capacity": 10}, headers=coach_headers
    )
    assert forbidden.status_code == 403
    duplicate = client.post(
        "/courses", json={"name": course["name"].upper(), "durationMinutes": 60},
        headers=auth_headers,
    )
    assert duplicate.status_code == 409


def test_specific_course_card_validates_course_ids_on_create_and_update(client, auth_headers):
    course = _course(client, auth_headers, "指定卡课程")
    disabled = client.patch(
        f"/courses/{course['id']}", json={"enabled": False}, headers=auth_headers
    )
    assert disabled.status_code == 200

    valid = client.post(
        "/card-products",
        json={
            "name": "有效指定课程卡", "cardType": "times", "price": "300.00",
            "totalTimes": 10, "activationMode": "immediate",
            "applicableCourseScope": "specific",
            "specificCourseIds": [course["id"], course["id"]],
        },
        headers=auth_headers,
    )
    assert valid.status_code == 201, valid.text
    assert valid.json()["specificCourseIds"] == [course["id"]]

    malformed = client.post(
        "/card-products",
        json={
            "name": "格式错误指定课程卡", "cardType": "times", "price": "300.00",
            "totalTimes": 10, "activationMode": "immediate",
            "applicableCourseScope": "specific", "specificCourseIds": ["not-a-uuid"],
        },
        headers=auth_headers,
    )
    assert malformed.status_code == 422

    missing_id = str(uuid4())
    missing = client.post(
        "/card-products",
        json={
            "name": "不存在课程卡", "cardType": "times", "price": "300.00",
            "totalTimes": 10, "activationMode": "immediate",
            "applicableCourseScope": "specific", "specificCourseIds": [missing_id],
        },
        headers=auth_headers,
    )
    assert missing.status_code == 422
    assert missing.json()["detail"] == f"Specific course not found: {missing_id}"

    group = client.post(
        "/card-products",
        json={
            "name": "待更新团课卡", "cardType": "times", "price": "300.00",
            "totalTimes": 10, "activationMode": "immediate",
            "applicableCourseScope": "group",
        },
        headers=auth_headers,
    )
    assert group.status_code == 201
    invalid_update = client.patch(
        f"/card-products/{group.json()['id']}",
        json={"applicableCourseScope": "specific", "specificCourseIds": [missing_id]},
        headers=auth_headers,
    )
    assert invalid_update.status_code == 422
    unchanged = client.get(f"/card-products/{group.json()['id']}", headers=auth_headers)
    assert unchanged.json()["applicableCourseScope"] == "group"
    assert unchanged.json()["specificCourseIds"] is None


def test_schedule_conflicts_lifecycle_visibility_and_copy(client, auth_headers, coach_headers):
    course = _course(client, auth_headers, "排课流瑜伽")
    room = _room(client, auth_headers, "排课一号教室")
    room_two = _room(client, auth_headers, "排课二号教室")
    coach = _coach(client, auth_headers, course["id"], "排课李教练")
    start = datetime(2030, 1, 7, 10, 0, tzinfo=timezone(timedelta(hours=8)))

    created = _session(client, auth_headers, course, room, coach, start)
    assert created.status_code == 201, created.text
    first = created.json()
    assert first["courseName"] == course["name"]
    assert first["coachName"] == coach["name"]
    assert first["roomName"] == room["name"]

    overlap = _session(client, auth_headers, course, room_two, coach, start + timedelta(minutes=30))
    assert overlap.status_code == 409
    assert overlap.json()["detail"] == "coach_time_conflict"

    adjacent = _session(client, auth_headers, course, room, coach, start + timedelta(hours=1))
    assert adjacent.status_code == 201, adjacent.text

    hidden = client.get(
        "/class-sessions", params={"weekStart": SOURCE_WEEK.isoformat()}, headers=coach_headers
    )
    assert hidden.status_code == 200 and hidden.json()["items"] == []

    published = client.post(f"/class-sessions/{first['id']}/publish", headers=auth_headers)
    assert published.status_code == 200 and published.json()["status"] == "published"
    paused = client.post(f"/class-sessions/{first['id']}/pause", headers=auth_headers)
    assert paused.status_code == 200 and paused.json()["status"] == "paused"
    resumed = client.post(f"/class-sessions/{first['id']}/resume", headers=auth_headers)
    assert resumed.status_code == 200 and resumed.json()["status"] == "published"

    visible = client.get(
        "/class-sessions", params={"weekStart": SOURCE_WEEK.isoformat()}, headers=coach_headers
    )
    assert visible.status_code == 200
    assert [item["id"] for item in visible.json()["items"]] == [first["id"]]

    copy_payload = {
        "sourceWeekStart": SOURCE_WEEK.isoformat(),
        "targetWeekStart": TARGET_WEEK.isoformat(),
    }
    copy_headers = {**auth_headers, "Idempotency-Key": "copy-week-2030-01-14"}
    copied = client.post("/class-sessions/copy-week", json=copy_payload, headers=copy_headers)
    assert copied.status_code == 200, copied.text
    assert len(copied.json()["created"]) == 2
    for item in copied.json()["created"]:
        assert item["bookingOpenHoursBefore"] == 168
        assert item["bookingCloseMinutesBefore"] == 0
        assert item["cancelCutoffMinutesBefore"] == 120
    replay = client.post("/class-sessions/copy-week", json=copy_payload, headers=copy_headers)
    assert replay.status_code == 200 and replay.json() == copied.json()
    duplicate_copy = client.post(
        "/class-sessions/copy-week", json=copy_payload,
        headers={**auth_headers, "Idempotency-Key": "copy-week-2030-01-14-again"},
    )
    assert duplicate_copy.status_code == 200
    assert duplicate_copy.json()["created"] == []
    assert {item["reason"] for item in duplicate_copy.json()["conflicts"]} <= {
        "coach_time_conflict", "room_time_conflict",
    }

    early = client.post(
        f"/class-sessions/{first['id']}/complete",
        headers={**auth_headers, "Idempotency-Key": "complete-too-early"},
    )
    assert early.status_code == 409

    cancelled = client.post(
        f"/class-sessions/{first['id']}/cancel",
        headers={**auth_headers, "Idempotency-Key": "cancel-session-2030"},
    )
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    cancel_replay = client.post(
        f"/class-sessions/{first['id']}/cancel",
        headers={**auth_headers, "Idempotency-Key": "cancel-session-2030"},
    )
    assert cancel_replay.status_code == 200 and cancel_replay.json() == cancelled.json()


def test_completed_session_requires_end_time(client, auth_headers):
    course = _course(client, auth_headers, "已结束课程")
    room = _room(client, auth_headers, "已结束教室")
    coach = _coach(client, auth_headers, course["id"], "已结束教练")
    start = datetime(2020, 1, 6, 10, 0, tzinfo=timezone(timedelta(hours=8)))
    created = _session(client, auth_headers, course, room, coach, start).json()
    client.post(f"/class-sessions/{created['id']}/publish", headers=auth_headers)
    completed = client.post(
        f"/class-sessions/{created['id']}/complete",
        headers={**auth_headers, "Idempotency-Key": "complete-ended-session"},
    )
    assert completed.status_code == 200 and completed.json()["status"] == "completed"


def test_week_start_must_be_monday(client, auth_headers):
    response = client.get(
        "/class-sessions", params={"weekStart": "2030-01-08"}, headers=auth_headers
    )
    assert response.status_code == 422


def test_session_rejects_disabled_resources_room_overcapacity_and_terminal_updates(client, auth_headers):
    course = _course(client, auth_headers, "规则校验课程")
    room = _room(client, auth_headers, "规则校验教室", capacity=5)
    coach = _coach(client, auth_headers, course["id"], "规则校验教练")
    start = datetime(2030, 1, 8, 10, 0, tzinfo=timezone(timedelta(hours=8)))

    overcapacity = _session(client, auth_headers, course, room, coach, start, capacity=6)
    assert overcapacity.status_code == 409
    assert overcapacity.json()["detail"] == "Session capacity exceeds room capacity"

    created = _session(client, auth_headers, course, room, coach, start, capacity=5)
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]
    cancelled = client.post(
        f"/class-sessions/{session_id}/cancel",
        headers={**auth_headers, "Idempotency-Key": "cancel-terminal-update"},
    )
    assert cancelled.status_code == 200
    terminal_update = client.patch(
        f"/class-sessions/{session_id}", json={"capacity": 4}, headers=auth_headers
    )
    assert terminal_update.status_code == 409

    disabled = client.patch(
        f"/courses/{course['id']}", json={"enabled": False}, headers=auth_headers
    )
    assert disabled.status_code == 200
    disabled_resource = _session(
        client, auth_headers, course, room, coach, start + timedelta(hours=2), capacity=5
    )
    assert disabled_resource.status_code == 409
    assert disabled_resource.json()["detail"] == "Course is disabled"
