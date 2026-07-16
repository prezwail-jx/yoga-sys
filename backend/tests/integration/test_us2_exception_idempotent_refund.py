from datetime import date

from sqlalchemy import text

from app.api.deps.business_clock import get_business_today
from app.main import app

TODAY = date(2026, 7, 16)

def _headers(auth_headers, key):
    return {**auth_headers, "Idempotency-Key": key}

def _purchase(client, auth_headers, phone="13800003301"):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    member = client.post("/members", json={"name": "退款会员", "phone": phone, "joinDate": TODAY.isoformat()}, headers=auth_headers).json()
    product = client.post("/card-products", json={"name": "可退款次卡", "cardType": "times", "price": "500.00", "totalTimes": 10, "validDays": 90, "activationMode": "immediate", "applicableCourseScope": "group", "absenceDeductEnabled": True, "cancelRefundEnabled": True}, headers=auth_headers).json()
    purchase = client.post("/transactions", json={"txnType": "purchase", "memberId": member["id"], "cardProductId": product["id"]}, headers=_headers(auth_headers, f"purchase-{phone}")).json()
    return member, purchase

def test_refund_replay_returns_same_transaction_without_second_mutation(client, auth_headers, db):
    member, purchase = _purchase(client, auth_headers)
    payload = {"txnType": "refund", "memberId": member["id"], "memberCardId": purchase["memberCard"]["id"], "originTransactionId": purchase["transaction"]["id"], "reason": "当天误购"}
    headers = _headers(auth_headers, "refund-us2-repeat-01")
    first, second = client.post("/transactions", json=payload, headers=headers), client.post("/transactions", json=payload, headers=headers)
    assert first.status_code == second.status_code == 200 and first.json() == second.json()
    assert first.json()["memberCard"]["status"] == "closed"
    assert db.execute(text("SELECT count(*) FROM card_transaction WHERE txn_type = 'refund'")).scalar_one() == 1

def test_same_idempotency_key_with_different_payload_returns_conflict(client, auth_headers):
    member1, purchase1 = _purchase(client, auth_headers, "13800003302")
    member2, purchase2 = _purchase(client, auth_headers, "13800003303")
    headers = _headers(auth_headers, "refund-us2-conflict-01")
    first = client.post("/transactions", json={"txnType": "refund", "memberId": member1["id"], "memberCardId": purchase1["memberCard"]["id"], "originTransactionId": purchase1["transaction"]["id"]}, headers=headers)
    second = client.post("/transactions", json={"txnType": "refund", "memberId": member2["id"], "memberCardId": purchase2["memberCard"]["id"], "originTransactionId": purchase2["transaction"]["id"]}, headers=headers)
    assert first.status_code == 200 and second.status_code == 409

def test_refund_rejects_when_card_has_later_transaction(client, auth_headers):
    member, purchase = _purchase(client, auth_headers, "13800003304")
    card_id = purchase["memberCard"]["id"]
    assert client.post("/transactions", json={"txnType": "renew", "memberId": member["id"], "memberCardId": card_id}, headers=_headers(auth_headers, "refund-us2-later-renew")).status_code == 200
    response = client.post("/transactions", json={"txnType": "refund", "memberId": member["id"], "memberCardId": card_id, "originTransactionId": purchase["transaction"]["id"]}, headers=_headers(auth_headers, "refund-us2-rejected"))
    assert response.status_code == 409

def test_coach_cannot_create_transaction(client, coach_headers, auth_headers):
    member, purchase = _purchase(client, auth_headers, "13800003305")
    response = client.post("/transactions", json={"txnType": "renew", "memberId": member["id"], "memberCardId": purchase["memberCard"]["id"]}, headers=_headers(coach_headers, "coach-renew-denied"))
    assert response.status_code == 403
