from datetime import date, datetime, timedelta, timezone

from app.api.deps.business_clock import get_business_now, get_business_today
from app.main import app


TODAY = date(2030, 1, 7)
NOW = datetime(2030, 1, 7, 9, 0, tzinfo=timezone.utc)


def _key(headers: dict[str, str], value: str) -> dict[str, str]:
    return {**headers, "Idempotency-Key": value}


def _login(client, username: str) -> dict[str, str]:
    response = client.post(
        "/auth/login", json={"username": username, "password": "secure123"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _member(client, admin_headers, suffix: str):
    response = client.post(
        "/members",
        json={
            "name": f"小程序会员{suffix}",
            "phone": f"1398000{int(suffix):04d}",
            "joinDate": TODAY.isoformat(),
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    member = response.json()
    username = f"mini.member.{suffix}"
    account = client.post(
        f"/members/{member['id']}/account",
        json={"username": username, "initialPassword": "secure123"},
        headers=_key(admin_headers, f"bind-mini-member-{suffix}"),
    )
    assert account.status_code == 201, account.text
    return member, _login(client, username)


def _product(client, admin_headers, name: str, scope: str):
    response = client.post(
        "/card-products",
        json={
            "name": name,
            "cardType": "times" if scope == "group" else "private",
            "price": "600.00",
            "totalTimes": 10,
            "validDays": 90,
            "activationMode": "immediate",
            "applicableCourseScope": scope,
            "absenceDeductEnabled": True,
            "cancelRefundEnabled": True,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _purchase(client, admin_headers, member_id: str, product_id: str, key: str):
    response = client.post(
        "/transactions",
        json={"txnType": "purchase", "memberId": member_id, "cardProductId": product_id},
        headers=_key(admin_headers, key),
    )
    assert response.status_code == 200, response.text
    return response.json()["memberCard"]


def _catalog(client, admin_headers):
    course = client.post(
        "/courses",
        json={"name": "小程序隔离团课", "durationMinutes": 60},
        headers=admin_headers,
    ).json()
    room = client.post(
        "/rooms", json={"name": "小程序隔离教室", "capacity": 10}, headers=admin_headers
    ).json()
    coach = client.post(
        "/coaches", json={"name": "小程序隔离教练"}, headers=admin_headers
    ).json()
    return course, room, coach


def _published_session(client, admin_headers, course, room, coach):
    start_at = NOW + timedelta(days=2)
    created = client.post(
        "/class-sessions",
        json={
            "courseId": course["id"],
            "roomId": room["id"],
            "coachProfileId": coach["id"],
            "startAt": start_at.isoformat(),
            "endAt": (start_at + timedelta(hours=1)).isoformat(),
            "capacity": 10,
            "bookingOpenHoursBefore": 168,
            "bookingCloseMinutesBefore": 0,
            "cancelCutoffMinutesBefore": 30,
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    published = client.post(
        f"/class-sessions/{created.json()['id']}/publish", headers=admin_headers
    )
    assert published.status_code == 200, published.text
    return published.json()


def test_member_tokens_isolate_group_bookings_and_self_service_cards(client, auth_headers):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    app.dependency_overrides[get_business_now] = lambda: NOW
    member_a, headers_a = _member(client, auth_headers, "8101")
    member_b, headers_b = _member(client, auth_headers, "8102")
    product = _product(client, auth_headers, "小程序团课卡", "group")
    card_a = _purchase(client, auth_headers, member_a["id"], product["id"], "mini-card-a-8101")
    card_b = _purchase(client, auth_headers, member_b["id"], product["id"], "mini-card-b-8102")
    course, room, coach = _catalog(client, auth_headers)
    class_session = _published_session(client, auth_headers, course, room, coach)

    booked = client.post(
        f"/class-sessions/{class_session['id']}/bookings",
        json={},
        headers=_key(headers_a, "mini-class-book-8101"),
    )
    assert booked.status_code == 201, booked.text
    assert booked.json()["memberId"] == member_a["id"]
    own_history = client.get("/members/me/bookings", headers=headers_a)
    other_history = client.get("/members/me/bookings", headers=headers_b)
    assert [item["id"] for item in own_history.json()["items"]] == [booked.json()["id"]]
    assert other_history.json()["items"] == []

    forged = client.post(
        f"/class-sessions/{class_session['id']}/bookings",
        json={"memberId": member_a["id"]},
        headers=_key(headers_b, "mini-forged-class-8102"),
    )
    assert forged.status_code == 403
    cross_cancel = client.post(
        f"/class-bookings/{booked.json()['id']}/cancel",
        json={"reason": "越权取消"},
        headers=_key(headers_b, "mini-forged-cancel-8102"),
    )
    assert cross_cancel.status_code == 403
    owner_history_after = client.get("/members/me/bookings", headers=headers_a)
    assert owner_history_after.json()["items"][0]["status"] == "reserved"

    cards_a = client.get("/members/me/cards", headers=headers_a)
    cards_b = client.get("/members/me/cards", headers=headers_b)
    assert [item["id"] for item in cards_a.json()["items"]] == [card_a["id"]]
    assert [item["id"] for item in cards_b.json()["items"]] == [card_b["id"]]
    cross_member_cards = client.get(f"/members/{member_a['id']}/cards", headers=headers_b)
    assert cross_member_cards.status_code == 403


def test_member_tokens_isolate_private_bookings_and_ignore_forged_member_id(client, auth_headers):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    app.dependency_overrides[get_business_now] = lambda: NOW
    member_a, headers_a = _member(client, auth_headers, "8201")
    member_b, headers_b = _member(client, auth_headers, "8202")
    _, _, coach = _catalog(client, auth_headers)
    slot_start = NOW + timedelta(days=3)
    slot = client.post(
        "/private-slots",
        json={
            "coachProfileId": coach["id"],
            "startAt": slot_start.isoformat(),
            "endAt": (slot_start + timedelta(hours=1)).isoformat(),
        },
        headers=auth_headers,
    )
    assert slot.status_code == 201, slot.text

    requested = client.post(
        "/private-bookings",
        json={
            "availabilityId": slot.json()["id"],
            "memberMessage": "本人私教申请",
            "memberId": member_b["id"],
        },
        headers=_key(headers_a, "mini-private-book-8201"),
    )
    assert requested.status_code == 201, requested.text
    assert requested.json()["memberId"] == member_a["id"]
    assert client.get("/private-bookings", headers=headers_a).json()["total"] == 1
    assert client.get("/private-bookings", headers=headers_b).json()["total"] == 0

    cross_read = client.get(
        f"/private-bookings/{requested.json()['id']}", headers=headers_b
    )
    assert cross_read.status_code == 403
    cross_cancel = client.post(
        f"/private-bookings/{requested.json()['id']}/cancel",
        json={"reason": "越权取消"},
        headers=_key(headers_b, "mini-private-cancel-8202"),
    )
    assert cross_cancel.status_code == 403
    owner_read = client.get(
        f"/private-bookings/{requested.json()['id']}", headers=headers_a
    )
    assert owner_read.status_code == 200
    assert owner_read.json()["status"] == "pending"
