from datetime import date

from app.api.deps.business_clock import get_business_today
from app.main import app

TODAY = date(2026, 7, 16)

def _headers(auth_headers, key):
    return {**auth_headers, "Idempotency-Key": key}

def _member(client, auth_headers, phone="13800003101"):
    response = client.post("/members", json={"name": "US2会员", "phone": phone, "joinDate": TODAY.isoformat()}, headers=auth_headers)
    assert response.status_code == 201
    return response.json()

def _product(client, auth_headers, activation_mode="immediate"):
    response = client.post("/card-products", json={"name": "20次卡", "cardType": "times", "price": "1200.00", "totalTimes": 20, "validDays": 180, "activationMode": activation_mode, "applicableCourseScope": "group", "absenceDeductEnabled": True, "cancelRefundEnabled": True}, headers=auth_headers)
    assert response.status_code == 201
    return response.json()

def test_purchase_renew_reissue_and_extend_lifecycle(client, auth_headers):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    member, product = _member(client, auth_headers), _product(client, auth_headers)
    purchased = client.post("/transactions", json={"txnType": "purchase", "memberId": member["id"], "cardProductId": product["id"]}, headers=_headers(auth_headers, "purchase-us2-0001"))
    assert purchased.status_code == 200
    body, card = purchased.json(), purchased.json()["memberCard"]
    assert (card["status"], card["remainingTimes"], card["openedOn"], card["expiresOn"]) == ("active", 20, "2026-07-16", "2027-01-11")
    assert body["transaction"]["amount"] == "1200.00"
    renewed = client.post("/transactions", json={"txnType": "renew", "memberId": member["id"], "memberCardId": card["id"]}, headers=_headers(auth_headers, "renew-us2-0001"))
    assert renewed.status_code == 200
    assert renewed.json()["memberCard"]["remainingTimes"] == 40
    assert renewed.json()["memberCard"]["expiresOn"] == "2027-07-10"
    extended = client.post("/transactions", json={"txnType": "extend", "memberId": member["id"], "memberCardId": card["id"], "validDaysDelta": 5, "reason": "活动赠送"}, headers=_headers(auth_headers, "extend-us2-0001"))
    assert extended.status_code == 200
    assert extended.json()["memberCard"]["expiresOn"] == "2027-07-15"
    reissued = client.post("/transactions", json={"txnType": "reissue", "memberId": member["id"], "memberCardId": card["id"], "reason": "补发新卡"}, headers=_headers(auth_headers, "reissue-us2-0001"))
    assert reissued.status_code == 200
    new_card = reissued.json()["memberCard"]
    assert new_card["id"] != card["id"] and new_card["sourceMemberCardId"] == card["id"]
    assert new_card["remainingTimes"] == 40
    cards = client.get(f"/members/{member['id']}/cards", headers=auth_headers)
    assert cards.status_code == 200 and cards.json()["total"] == 2
    assert {item["status"] for item in cards.json()["items"]} == {"active", "closed"}

def test_pending_first_booking_card_has_no_open_or_expiry_date(client, auth_headers):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    member, product = _member(client, auth_headers, "13800003102"), _product(client, auth_headers, "first_booking")
    response = client.post("/transactions", json={"txnType": "purchase", "memberId": member["id"], "cardProductId": product["id"]}, headers=_headers(auth_headers, "purchase-us2-pending"))
    assert response.status_code == 200
    card = response.json()["memberCard"]
    assert card["status"] == "pending_activation" and card["openedOn"] is None and card["expiresOn"] is None

def test_freeze_and_manual_unfreeze_extend_by_natural_days(client, auth_headers):
    current = {"today": TODAY}
    app.dependency_overrides[get_business_today] = lambda: current["today"]
    member, product = _member(client, auth_headers, "13800003103"), _product(client, auth_headers)
    card = client.post("/transactions", json={"txnType": "purchase", "memberId": member["id"], "cardProductId": product["id"]}, headers=_headers(auth_headers, "purchase-us2-freeze")).json()["memberCard"]
    frozen = client.post(f"/member-cards/{card['id']}/freeze", json={"frozenUntil": "2026-07-26", "reason": "出差"}, headers=_headers(auth_headers, "freeze-us2-0001"))
    assert frozen.status_code == 200 and frozen.json()["memberCard"]["status"] == "frozen"
    current["today"] = date(2026, 7, 20)
    unfrozen = client.post(f"/member-cards/{card['id']}/unfreeze", json={"reason": "提前返程"}, headers=_headers(auth_headers, "unfreeze-us2-0001"))
    assert unfrozen.status_code == 200
    result = unfrozen.json()["memberCard"]
    assert (result["status"], result["totalFrozenDays"], result["expiresOn"]) == ("active", 4, "2027-01-15")
