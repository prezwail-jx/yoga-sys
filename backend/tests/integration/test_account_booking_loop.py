from datetime import date, datetime, timedelta, timezone

from app.api.deps.business_clock import get_business_now, get_business_today
from app.main import app


TODAY = date(2030, 1, 7)
NOW = datetime(2030, 1, 7, 9, 0, tzinfo=timezone.utc)


def _headers(client, username, password):
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _member(client, admin_headers, phone):
    response = client.post(
        "/members",
        json={"name": f"会员{phone[-4:]}", "phone": phone, "joinDate": TODAY.isoformat()},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _product(client, admin_headers, name, scope="group", course_ids=None):
    response = client.post(
        "/card-products",
        json={
            "name": name, "cardType": "times", "price": "300.00",
            "totalTimes": 2, "validDays": 90, "activationMode": "immediate",
            "applicableCourseScope": scope, "specificCourseIds": course_ids,
            "absenceDeductEnabled": False, "cancelRefundEnabled": False,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _purchase(client, admin_headers, member_id, product_id, key):
    response = client.post(
        "/transactions",
        json={"txnType": "purchase", "memberId": member_id, "cardProductId": product_id},
        headers={**admin_headers, "Idempotency-Key": key},
    )
    assert response.status_code == 200, response.text
    return response.json()["memberCard"]


def _catalog(client, admin_headers):
    course = client.post(
        "/courses", json={"name": "预约流瑜伽", "durationMinutes": 60}, headers=admin_headers
    ).json()
    room = client.post(
        "/rooms", json={"name": "预约教室", "capacity": 10}, headers=admin_headers
    ).json()
    coach = client.post(
        "/coaches", json={"name": "预约教练", "specialtyCourseIds": [course["id"]]},
        headers=admin_headers,
    ).json()
    return course, room, coach


def _session(client, admin_headers, course, room, coach, start_at):
    response = client.post(
        "/class-sessions",
        json={
            "courseId": course["id"], "roomId": room["id"],
            "coachProfileId": coach["id"], "startAt": start_at.isoformat(),
            "endAt": (start_at + timedelta(hours=1)).isoformat(), "capacity": 10,
            "bookingOpenHoursBefore": 168, "bookingCloseMinutesBefore": 0,
            "cancelCutoffMinutesBefore": 30,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    value = response.json()
    published = client.post(f"/class-sessions/{value['id']}/publish", headers=admin_headers)
    assert published.status_code == 200, published.text
    return published.json()


def _bind_account(client, admin_headers, path, username, key):
    response = client.post(
        path, json={"username": username, "initialPassword": "secure123"},
        headers={**admin_headers, "Idempotency-Key": key},
    )
    assert response.status_code == 201, response.text
    return response


def test_admin_creates_member_and_coach_resource_scoped_accounts(client, auth_headers):
    member = _member(client, auth_headers, "13800006101")
    course, _, coach = _catalog(client, auth_headers)
    member_account = _bind_account(
        client, auth_headers, f"/members/{member['id']}/account", "Member.6101", "bind-member-6101"
    )
    replay = _bind_account(
        client, auth_headers, f"/members/{member['id']}/account", "Member.6101", "bind-member-6101"
    )
    assert replay.json() == member_account.json()
    assert "password" not in str(member_account.json()).lower()

    coach_account = _bind_account(
        client, auth_headers, f"/coaches/{coach['id']}/account", "Coach.6101", "bind-coach-6101"
    )
    assert coach_account.json()["coachProfileId"] == coach["id"]

    member_me = client.get("/auth/me", headers=_headers(client, "member.6101", "secure123"))
    coach_me = client.get("/auth/me", headers=_headers(client, "coach.6101", "secure123"))
    assert member_me.json()["memberId"] == member["id"]
    assert coach_me.json()["coachProfileId"] == coach["id"]

    duplicate = client.post(
        f"/members/{member['id']}/account",
        json={"username": "member.other", "initialPassword": "secure123"},
        headers={**auth_headers, "Idempotency-Key": "bind-member-again"},
    )
    assert duplicate.status_code == 409


def test_booking_checkin_absence_and_venue_force_refund(client, auth_headers):
    app.dependency_overrides[get_business_now] = lambda: NOW
    app.dependency_overrides[get_business_today] = lambda: TODAY
    member = _member(client, auth_headers, "13800006111")
    absent_member = _member(client, auth_headers, "13800006112")
    ineligible_member = _member(client, auth_headers, "13800006113")
    course, room, coach = _catalog(client, auth_headers)

    private_product = _product(client, auth_headers, "不适用私教卡", scope="private")
    group_product = _product(client, auth_headers, "团课核销卡")
    _purchase(client, auth_headers, member["id"], private_product["id"], "buy-private-6111")
    _purchase(client, auth_headers, ineligible_member["id"], private_product["id"], "buy-private-6113")
    group_card = _purchase(client, auth_headers, member["id"], group_product["id"], "buy-group-6111")
    absent_card = _purchase(client, auth_headers, absent_member["id"], group_product["id"], "buy-group-6112")

    _bind_account(
        client, auth_headers, f"/members/{member['id']}/account", "member.6111", "bind-member-6111"
    )
    _bind_account(
        client, auth_headers, f"/coaches/{coach['id']}/account", "coach.6111", "bind-coach-6111"
    )
    member_headers = _headers(client, "member.6111", "secure123")
    coach_headers = _headers(client, "coach.6111", "secure123")

    class_session = _session(client, auth_headers, course, room, coach, NOW + timedelta(hours=1))
    ineligible = client.post(
        f"/class-sessions/{class_session['id']}/bookings",
        json={"memberId": ineligible_member["id"]},
        headers={**auth_headers, "Idempotency-Key": "ineligible-booking-6113"},
    )
    assert ineligible.status_code == 409
    assert client.get(
        f"/class-sessions/{class_session['id']}/bookings", headers=auth_headers
    ).json()["items"] == []
    booking_headers = {**member_headers, "Idempotency-Key": "member-booking-6111"}
    booked = client.post(
        f"/class-sessions/{class_session['id']}/bookings", json={}, headers=booking_headers
    )
    assert booked.status_code == 201, booked.text
    replay = client.post(
        f"/class-sessions/{class_session['id']}/bookings", json={}, headers=booking_headers
    )
    assert replay.status_code == 201 and replay.json() == booked.json()
    booking = booked.json()
    assert booking["bookedById"] is None

    timeline = client.get(
        f"/members/{member['id']}/timeline",
        params={"businessRef": booking["id"]}, headers=auth_headers,
    ).json()["items"]
    assert timeline[0]["memberCardId"] == group_card["id"]

    proxy = client.post(
        f"/class-sessions/{class_session['id']}/bookings",
        json={"memberId": absent_member["id"]},
        headers={**auth_headers, "Idempotency-Key": "admin-proxy-6112"},
    )
    assert proxy.status_code == 201, proxy.text

    app.dependency_overrides[get_business_now] = lambda: NOW + timedelta(minutes=29)
    too_early = client.post(
        f"/class-bookings/{booking['id']}/check-in",
        headers={**coach_headers, "Idempotency-Key": "checkin-too-early"},
    )
    assert too_early.status_code == 409
    app.dependency_overrides[get_business_now] = lambda: NOW + timedelta(minutes=30)
    checkin_headers = {**coach_headers, "Idempotency-Key": "checkin-member-6111"}
    checked_in = client.post(
        f"/class-bookings/{booking['id']}/check-in",
        headers=checkin_headers,
    )
    assert checked_in.status_code == 200 and checked_in.json()["status"] == "checked_in"
    checkin_replay = client.post(
        f"/class-bookings/{booking['id']}/check-in", headers=checkin_headers
    )
    assert checkin_replay.status_code == 200 and checkin_replay.json() == checked_in.json()

    app.dependency_overrides[get_business_now] = lambda: NOW + timedelta(hours=2, minutes=1)
    completed = client.post(
        f"/class-sessions/{class_session['id']}/complete",
        headers={**auth_headers, "Idempotency-Key": "complete-session-6111"},
    )
    assert completed.status_code == 200 and completed.json()["status"] == "completed"
    roster = client.get(
        f"/class-sessions/{class_session['id']}/bookings", headers=auth_headers
    ).json()["items"]
    assert {item["memberId"]: item["status"] for item in roster} == {
        member["id"]: "checked_in", absent_member["id"]: "absent",
    }
    cards = client.get(f"/members/{absent_member['id']}/cards", headers=auth_headers).json()["items"]
    assert next(item for item in cards if item["id"] == absent_card["id"])["remainingTimes"] == 2

    app.dependency_overrides[get_business_now] = lambda: NOW
    cancel_session = _session(client, auth_headers, course, room, coach, NOW + timedelta(hours=4))
    venue_booking = client.post(
        f"/class-sessions/{cancel_session['id']}/bookings",
        json={"memberId": absent_member["id"]},
        headers={**auth_headers, "Idempotency-Key": "venue-booking-6112"},
    ).json()
    cancelled = client.post(
        f"/class-sessions/{cancel_session['id']}/cancel",
        headers={**auth_headers, "Idempotency-Key": "venue-cancel-6112"},
    )
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    cancelled_booking = client.get(
        f"/class-sessions/{cancel_session['id']}/bookings", headers=auth_headers
    ).json()["items"][0]
    assert cancelled_booking["id"] == venue_booking["id"]
    assert cancelled_booking["status"] == "cancelled"
    cards = client.get(f"/members/{absent_member['id']}/cards", headers=auth_headers).json()["items"]
    assert next(item for item in cards if item["id"] == absent_card["id"])["remainingTimes"] == 2


def test_member_cancel_cutoff_replay_terminal_exclusion_and_rebook(client, auth_headers):
    app.dependency_overrides[get_business_now] = lambda: NOW
    app.dependency_overrides[get_business_today] = lambda: TODAY
    member = _member(client, auth_headers, "13800006121")
    course, room, coach = _catalog(client, auth_headers)
    product = _product(client, auth_headers, "取消重约卡")
    _purchase(client, auth_headers, member["id"], product["id"], "buy-cancel-rebook-6121")
    _bind_account(
        client, auth_headers, f"/members/{member['id']}/account",
        "member.6121", "bind-member-6121",
    )
    member_headers = _headers(client, "member.6121", "secure123")
    class_session = _session(client, auth_headers, course, room, coach, NOW + timedelta(hours=1))

    booked = client.post(
        f"/class-sessions/{class_session['id']}/bookings", json={},
        headers={**member_headers, "Idempotency-Key": "member-booking-6121"},
    )
    assert booked.status_code == 201, booked.text
    booking = booked.json()

    app.dependency_overrides[get_business_now] = lambda: NOW + timedelta(minutes=31)
    late = client.post(
        f"/class-bookings/{booking['id']}/cancel", json={"reason": "late"},
        headers={**member_headers, "Idempotency-Key": "late-cancel-6121"},
    )
    assert late.status_code == 409

    app.dependency_overrides[get_business_now] = lambda: NOW + timedelta(minutes=29)
    cancel_headers = {**member_headers, "Idempotency-Key": "cancel-booking-6121"}
    cancelled = client.post(
        f"/class-bookings/{booking['id']}/cancel", json={"reason": "changed plans"},
        headers=cancel_headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    replay = client.post(
        f"/class-bookings/{booking['id']}/cancel", json={"reason": "changed plans"},
        headers=cancel_headers,
    )
    assert replay.status_code == 200 and replay.json() == cancelled.json()

    terminal_conflict = client.post(
        f"/class-bookings/{booking['id']}/check-in",
        headers={**auth_headers, "Idempotency-Key": "checkin-cancelled-6121"},
    )
    assert terminal_conflict.status_code == 409

    app.dependency_overrides[get_business_now] = lambda: NOW
    rebooked = client.post(
        f"/class-sessions/{class_session['id']}/bookings", json={},
        headers={**member_headers, "Idempotency-Key": "member-rebook-6121"},
    )
    assert rebooked.status_code == 201, rebooked.text
    assert rebooked.json()["id"] != booking["id"]
