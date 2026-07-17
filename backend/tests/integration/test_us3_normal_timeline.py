from datetime import date

from app.api.deps.business_clock import get_business_today
from app.main import app

TODAY = date(2026, 7, 17)

def _key(headers: dict[str, str], value: str) -> dict[str, str]:
    return {**headers, "Idempotency-Key": value}

def _member(client, headers, phone: str):
    response = client.post("/members", json={"name": "US3会员", "phone": phone, "joinDate": TODAY.isoformat()}, headers=headers)
    assert response.status_code == 201
    return response.json()

def _times_product(client, headers, *, name: str, total_times: int, valid_days: int):
    response = client.post("/card-products", json={"name": name, "cardType": "times", "price": "600.00", "totalTimes": total_times, "validDays": valid_days, "activationMode": "immediate", "applicableCourseScope": "group", "absenceDeductEnabled": True, "cancelRefundEnabled": True}, headers=headers)
    assert response.status_code == 201
    return response.json()

def _purchase(client, headers, member_id: str, product_id: str, key: str):
    response = client.post("/transactions", json={"txnType": "purchase", "memberId": member_id, "cardProductId": product_id}, headers=_key(headers, key))
    assert response.status_code == 200
    return response.json()

def _writeoff(client, headers, member_id: str, business_ref: str, event_type: str, key: str):
    return client.post("/writeoff/events", json={"memberId": member_id, "businessRef": business_ref, "eventType": event_type}, headers=_key(headers, key))

def test_admin_replays_purchase_reserve_and_checkin_chain_from_timeline(client, auth_headers):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    member = _member(client, auth_headers, "13800004601")
    later = _times_product(client, auth_headers, name="晚到期卡", total_times=10, valid_days=180)
    earlier = _times_product(client, auth_headers, name="早到期卡", total_times=5, valid_days=30)
    _purchase(client, auth_headers, member["id"], later["id"], "us3-purchase-later")
    early_purchase = _purchase(client, auth_headers, member["id"], earlier["id"], "us3-purchase-earlier")
    reserved = _writeoff(client, auth_headers, member["id"], "booking-us3-001", "reserve_hold", "us3-reserve-001")
    assert reserved.status_code == 200
    reserve_body = reserved.json()
    assert reserve_body["memberCardId"] == early_purchase["memberCard"]["id"]
    assert reserve_body["timesDelta"] == -1 and reserve_body["sequenceNo"] == 1
    checked_in = _writeoff(client, auth_headers, member["id"], "booking-us3-001", "checkin_commit", "us3-checkin-001")
    assert checked_in.status_code == 200
    assert checked_in.json()["previousEventId"] == reserve_body["id"] and checked_in.json()["timesDelta"] == 0
    cards = client.get(f"/members/{member['id']}/cards", headers=auth_headers).json()["items"]
    selected = next(card for card in cards if card["id"] == reserve_body["memberCardId"])
    assert selected["remainingTimes"] == 4 and selected["usedTimes"] == 1
    timeline = client.get(f"/members/{member['id']}/timeline", headers=auth_headers)
    assert timeline.status_code == 200
    actions = [item["action"] for item in timeline.json()["items"]]
    assert {"purchase", "reserve_hold", "checkin_commit"} <= set(actions)
    purchase_event = next(item for item in timeline.json()["items"] if item["action"] == "purchase" and item["memberCardId"] == early_purchase["memberCard"]["id"])
    assert purchase_event["productName"] == "早到期卡"
    assert purchase_event["cardType"] == "times"
    assert purchase_event["amount"] == "600.00"
    assert purchase_event["timesDelta"] == 5
    assert purchase_event["validDaysDelta"] == 30
    chain = [item for item in timeline.json()["items"] if item.get("businessRef") == "booking-us3-001"]
    assert {item["action"] for item in chain} == {"reserve_hold", "checkin_commit"}
    assert all(item["operatorId"] == "admin" for item in chain)

def test_same_business_event_replays_without_second_entitlement_change(client, auth_headers):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    member = _member(client, auth_headers, "13800004602")
    product = _times_product(client, auth_headers, name="幂等卡", total_times=3, valid_days=90)
    card = _purchase(client, auth_headers, member["id"], product["id"], "us3-purchase-idempotent")["memberCard"]
    first = _writeoff(client, auth_headers, member["id"], "booking-us3-idem", "reserve_hold", "us3-reserve-idem-1")
    replay = _writeoff(client, auth_headers, member["id"], "booking-us3-idem", "reserve_hold", "us3-reserve-idem-2")
    assert first.status_code == replay.status_code == 200 and first.json()["id"] == replay.json()["id"]
    cards = client.get(f"/members/{member['id']}/cards", headers=auth_headers).json()["items"]
    assert next(item for item in cards if item["id"] == card["id"])["remainingTimes"] == 2
