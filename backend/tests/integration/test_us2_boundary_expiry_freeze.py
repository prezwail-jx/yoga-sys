from datetime import date

from app.api.deps.business_clock import get_business_today
from app.main import app

def _headers(auth_headers, key):
    return {**auth_headers, "Idempotency-Key": key}

def _setup_card(client, auth_headers, current):
    app.dependency_overrides[get_business_today] = lambda: current["today"]
    member = client.post("/members", json={"name": "边界会员", "phone": "13800003201", "joinDate": "2026-07-01"}, headers=auth_headers).json()
    product = client.post("/card-products", json={"name": "10天期限卡", "cardType": "duration", "price": "300.00", "validDays": 10, "activationMode": "immediate", "applicableCourseScope": "group", "absenceDeductEnabled": False, "cancelRefundEnabled": False}, headers=auth_headers).json()
    card = client.post("/transactions", json={"txnType": "purchase", "memberId": member["id"], "cardProductId": product["id"]}, headers=_headers(auth_headers, "boundary-purchase-01")).json()["memberCard"]
    return member, card

def test_expiry_reminder_and_access_time_expiry_reconciliation(client, auth_headers):
    current = {"today": date(2026, 7, 1)}
    member, card = _setup_card(client, auth_headers, current)
    assert card["expiresOn"] == "2026-07-10" and card["remindOn"] == "2026-07-03"
    current["today"] = date(2026, 7, 3)
    reminder = client.get(f"/members/{member['id']}/cards", headers=auth_headers).json()["items"][0]
    assert reminder["status"] == "active" and reminder["expiringSoon"] is True
    current["today"] = date(2026, 7, 10)
    assert client.get(f"/members/{member['id']}/cards", headers=auth_headers).json()["items"][0]["status"] == "active"
    current["today"] = date(2026, 7, 11)
    expired = client.get(f"/members/{member['id']}/cards", headers=auth_headers).json()["items"][0]
    assert expired["status"] == "expired" and expired["expiringSoon"] is False

def test_frozen_card_auto_unfreezes_before_expiry_reconciliation(client, auth_headers):
    current = {"today": date(2026, 7, 1)}
    member, card = _setup_card(client, auth_headers, current)
    response = client.post(f"/member-cards/{card['id']}/freeze", json={"frozenUntil": "2026-07-15", "reason": "长期出差"}, headers=_headers(auth_headers, "boundary-freeze-01"))
    assert response.status_code == 200
    current["today"] = date(2026, 7, 15)
    result = client.get(f"/members/{member['id']}/cards", headers=auth_headers).json()["items"][0]
    assert (result["status"], result["totalFrozenDays"], result["expiresOn"]) == ("active", 14, "2026-07-24")

def test_expired_card_renewal_reactivates_from_renewal_day(client, auth_headers):
    current = {"today": date(2026, 7, 1)}
    member, card = _setup_card(client, auth_headers, current)
    current["today"] = date(2026, 8, 1)
    renewed = client.post("/transactions", json={"txnType": "renew", "memberId": member["id"], "memberCardId": card["id"]}, headers=_headers(auth_headers, "boundary-renew-expired"))
    assert renewed.status_code == 200
    result = renewed.json()["memberCard"]
    assert (result["status"], result["openedOn"], result["expiresOn"]) == ("active", "2026-08-01", "2026-08-10")
