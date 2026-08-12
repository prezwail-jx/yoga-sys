from datetime import date, datetime, timedelta, timezone

from app.api.deps.business_clock import get_business_now, get_business_today
from app.main import app

TODAY = date(2030, 1, 7)
NOW = datetime(2030, 1, 7, 9, 0, tzinfo=timezone.utc)


def _key(headers: dict[str, str], value: str) -> dict[str, str]:
    return {**headers, "Idempotency-Key": value}


def _login(client, username: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": "secure123"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _member(client, admin_headers, suffix: str):
    response = client.post(
        "/members",
        json={"name": f"私教资格会员{suffix}", "phone": f"1399000{int(suffix):04d}", "joinDate": TODAY.isoformat()},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    member = response.json()
    username = f"pt.member.{suffix}"
    account = client.post(
        f"/members/{member['id']}/account",
        json={"username": username, "initialPassword": "secure123"},
        headers=_key(admin_headers, f"bind-pt-member-{suffix}"),
    )
    assert account.status_code == 201, account.text
    return member, _login(client, username)


def _coach(client, admin_headers, suffix: str):
    response = client.post("/coaches", json={"name": f"私教资格教练{suffix}"}, headers=admin_headers)
    assert response.status_code == 201, response.text
    coach = response.json()
    username = f"pt.coach.{suffix}"
    account = client.post(
        f"/coaches/{coach['id']}/account",
        json={"username": username, "initialPassword": "secure123"},
        headers=_key(admin_headers, f"bind-pt-coach-{suffix}"),
    )
    assert account.status_code == 201, account.text
    return coach, _login(client, username)


def _product(client, admin_headers, name: str, scope: str, *, card_type: str | None = None, activation: str = "immediate"):
    response = client.post(
        "/card-products",
        json={
            "name": name,
            "cardType": card_type or ("times" if scope == "group" else "private"),
            "price": "600.00",
            "totalTimes": 10,
            "validDays": 90,
            "activationMode": activation,
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


def _slot(client, coach_headers, *, coach_id: str | None = None, start_at: datetime | None = None, key: str = "pt-slot-1"):
    start_at = start_at or (NOW + timedelta(days=3))
    payload = {"startAt": start_at.isoformat(), "endAt": (start_at + timedelta(hours=1)).isoformat()}
    if coach_id:
        payload["coachProfileId"] = coach_id
    response = client.post("/private-slots", json=payload, headers=_key(coach_headers, key))
    assert response.status_code == 201, response.text
    return response.json()


def _request_booking(client, member_headers, slot_id: str, key: str):
    response = client.post(
        "/private-bookings",
        json={"availabilityId": slot_id, "memberMessage": "资格测试申请"},
        headers=_key(member_headers, key),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _freeze(client, admin_headers, card_id: str, key: str):
    response = client.post(
        f"/member-cards/{card_id}/freeze",
        json={"frozenUntil": (TODAY + timedelta(days=30)).isoformat(), "reason": "测试冻结"},
        headers=_key(admin_headers, key),
    )
    assert response.status_code == 200, response.text
    return response.json()["memberCard"]


def _set_card_state(db, card_id: str, **values):
    from sqlalchemy import update
    from app.domain.member_card import MemberCard
    db.execute(update(MemberCard).where(MemberCard.id == card_id).values(**values))
    db.flush()


def test_member_with_group_and_private_card_confirms_and_deducts_private(client, auth_headers):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    app.dependency_overrides[get_business_now] = lambda: NOW
    member, member_headers = _member(client, auth_headers, "7101")
    coach, coach_headers = _coach(client, auth_headers, "7101")
    group_product = _product(client, auth_headers, "资格团课卡", "group")
    private_product = _product(client, auth_headers, "资格私教卡", "private")
    group_card = _purchase(client, auth_headers, member["id"], group_product["id"], "pt-group-7101")
    private_card = _purchase(client, auth_headers, member["id"], private_product["id"], "pt-private-7101")
    slot = _slot(client, coach_headers, coach_id=coach["id"])
    booking = _request_booking(client, member_headers, slot["id"], "pt-book-7101")

    confirmed = client.post(
        f"/private-bookings/{booking['id']}/confirm",
        headers=_key(coach_headers, "pt-confirm-7101"),
    )
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body["status"] == "confirmed"
    assert body["memberCardId"] == private_card["id"]

    group_after = client.get(f"/members/{member['id']}/cards", headers=auth_headers).json()["items"]
    private_after = next(item for item in group_after if item["id"] == private_card["id"])
    group_after_card = next(item for item in group_after if item["id"] == group_card["id"])
    assert private_after["remainingTimes"] == 9
    assert group_after_card["remainingTimes"] == 10


def test_confirmation_requires_an_eligible_private_card(client, auth_headers):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    app.dependency_overrides[get_business_now] = lambda: NOW
    member, member_headers = _member(client, auth_headers, "7102")
    coach, coach_headers = _coach(client, auth_headers, "7102")
    slot = _slot(client, coach_headers, coach_id=coach["id"], key="pt-slot-7102")
    booking = _request_booking(client, member_headers, slot["id"], "pt-book-7102")

    rejected = client.post(
        f"/private-bookings/{booking['id']}/confirm",
        headers=_key(coach_headers, "pt-confirm-7102"),
    )
    assert rejected.status_code == 409, rejected.text
    assert client.get(f"/private-bookings/{booking['id']}", headers=coach_headers).json()["status"] == "pending"


def test_group_only_card_does_not_satisfy_private_confirmation(client, auth_headers):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    app.dependency_overrides[get_business_now] = lambda: NOW
    member, member_headers = _member(client, auth_headers, "7103")
    coach, coach_headers = _coach(client, auth_headers, "7103")
    group_product = _product(client, auth_headers, "资格团课卡", "group")
    _purchase(client, auth_headers, member["id"], group_product["id"], "pt-group-7103")
    slot = _slot(client, coach_headers, coach_id=coach["id"], key="pt-slot-7103")
    booking = _request_booking(client, member_headers, slot["id"], "pt-book-7103")

    rejected = client.post(
        f"/private-bookings/{booking['id']}/confirm",
        headers=_key(coach_headers, "pt-confirm-7103"),
    )
    assert rejected.status_code == 409, rejected.text


def test_frozen_private_card_rejects_confirmation(client, auth_headers, db):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    app.dependency_overrides[get_business_now] = lambda: NOW
    member, member_headers = _member(client, auth_headers, "7104")
    coach, coach_headers = _coach(client, auth_headers, "7104")
    private_product = _product(client, auth_headers, "资格私教卡", "private")
    private_card = _purchase(client, auth_headers, member["id"], private_product["id"], "pt-private-7104")
    _freeze(client, auth_headers, private_card["id"], "pt-freeze-7104")
    _set_card_state(db, private_card["id"], status="frozen")
    slot = _slot(client, coach_headers, coach_id=coach["id"], key="pt-slot-7104")
    booking = _request_booking(client, member_headers, slot["id"], "pt-book-7104")

    rejected = client.post(
        f"/private-bookings/{booking['id']}/confirm",
        headers=_key(coach_headers, "pt-confirm-7104"),
    )
    assert rejected.status_code == 409, rejected.text


def test_exhausted_private_card_rejects_confirmation(client, auth_headers, db):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    app.dependency_overrides[get_business_now] = lambda: NOW
    member, member_headers = _member(client, auth_headers, "7105")
    coach, coach_headers = _coach(client, auth_headers, "7105")
    private_product = _product(client, auth_headers, "资格私教卡", "private")
    private_card = _purchase(client, auth_headers, member["id"], private_product["id"], "pt-private-7105")
    _set_card_state(db, private_card["id"], remaining_times=0)
    slot = _slot(client, coach_headers, coach_id=coach["id"], key="pt-slot-7105")
    booking = _request_booking(client, member_headers, slot["id"], "pt-book-7105")

    rejected = client.post(
        f"/private-bookings/{booking['id']}/confirm",
        headers=_key(coach_headers, "pt-confirm-7105"),
    )
    assert rejected.status_code == 409, rejected.text


def test_expired_private_card_rejects_confirmation(client, auth_headers, db):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    app.dependency_overrides[get_business_now] = lambda: NOW
    member, member_headers = _member(client, auth_headers, "7106")
    coach, coach_headers = _coach(client, auth_headers, "7106")
    private_product = _product(client, auth_headers, "资格私教卡", "private")
    private_card = _purchase(client, auth_headers, member["id"], private_product["id"], "pt-private-7106")
    _set_card_state(db, private_card["id"], status="expired", expires_on=TODAY - timedelta(days=1))
    slot = _slot(client, coach_headers, coach_id=coach["id"], key="pt-slot-7106")
    booking = _request_booking(client, member_headers, slot["id"], "pt-book-7106")

    rejected = client.post(
        f"/private-bookings/{booking['id']}/confirm",
        headers=_key(coach_headers, "pt-confirm-7106"),
    )
    assert rejected.status_code == 409, rejected.text


def test_first_booking_private_card_activates_on_confirmation(client, auth_headers):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    app.dependency_overrides[get_business_now] = lambda: NOW
    member, member_headers = _member(client, auth_headers, "7107")
    coach, coach_headers = _coach(client, auth_headers, "7107")
    private_product = _product(client, auth_headers, "首次开私教卡", "private", activation="first_booking")
    private_card = _purchase(client, auth_headers, member["id"], private_product["id"], "pt-private-7107")
    assert private_card["status"] == "pending_activation"
    slot = _slot(client, coach_headers, coach_id=coach["id"], key="pt-slot-7107")
    booking = _request_booking(client, member_headers, slot["id"], "pt-book-7107")

    confirmed = client.post(
        f"/private-bookings/{booking['id']}/confirm",
        headers=_key(coach_headers, "pt-confirm-7107"),
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "confirmed"
    after = client.get(f"/members/{member['id']}/cards", headers=auth_headers).json()["items"]
    activated = next(item for item in after if item["id"] == private_card["id"])
    assert activated["status"] == "active"
    assert activated["remainingTimes"] == 9


def test_idempotent_confirmation_does_not_double_deduct(client, auth_headers):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    app.dependency_overrides[get_business_now] = lambda: NOW
    member, member_headers = _member(client, auth_headers, "7108")
    coach, coach_headers = _coach(client, auth_headers, "7108")
    private_product = _product(client, auth_headers, "资格私教卡", "private")
    private_card = _purchase(client, auth_headers, member["id"], private_product["id"], "pt-private-7108")
    slot = _slot(client, coach_headers, coach_id=coach["id"], key="pt-slot-7108")
    booking = _request_booking(client, member_headers, slot["id"], "pt-book-7108")

    first = client.post(
        f"/private-bookings/{booking['id']}/confirm",
        headers=_key(coach_headers, "pt-confirm-7108"),
    )
    second = client.post(
        f"/private-bookings/{booking['id']}/confirm",
        headers=_key(coach_headers, "pt-confirm-7108"),
    )
    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()
    after = client.get(f"/members/{member['id']}/cards", headers=auth_headers).json()["items"]
    private_after = next(item for item in after if item["id"] == private_card["id"])
    assert private_after["remainingTimes"] == 9
