from datetime import date
from uuid import UUID

from sqlalchemy import select

from app.api.deps.business_clock import get_business_today
from app.domain.audit_log import AuditLog
from app.domain.card_transaction import CardTransaction
from app.domain.member_card import MemberCard
from app.main import app


TODAY = date(2026, 8, 27)


def _headers(auth_headers, key):
    return {**auth_headers, "Idempotency-Key": key}


def _purchase(client, auth_headers, phone, *, card_type="times"):
    member = client.post(
        "/members",
        json={"name": "调次会员", "phone": phone, "joinDate": TODAY.isoformat()},
        headers=auth_headers,
    ).json()
    product_payload = {
        "name": "10次卡" if card_type == "times" else "月卡",
        "cardType": card_type,
        "price": "500.00",
        "validDays": 30,
        "activationMode": "immediate",
        "applicableCourseScope": "group",
    }
    if card_type == "times":
        product_payload["totalTimes"] = 10
    product = client.post("/card-products", json=product_payload, headers=auth_headers).json()
    purchase = client.post(
        "/transactions",
        json={"txnType": "purchase", "memberId": member["id"], "cardProductId": product["id"]},
        headers=_headers(auth_headers, f"purchase-adjust-{phone}"),
    ).json()
    return member, purchase["memberCard"]


def test_adjust_times_is_audited_idempotent_and_allows_closed_card(client, auth_headers, db):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    member, card = _purchase(client, auth_headers, "13800008101")
    path = f"/member-cards/{card['id']}/adjust-times"
    payload = {"timesDelta": 3, "reason": "  人工补偿  "}
    headers = _headers(auth_headers, "adjust-times-repeat-01")

    first = client.post(path, json=payload, headers=headers)
    second = client.post(path, json=payload, headers=headers)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["memberCard"]["remainingTimes"] == 13
    assert first.json()["memberCard"]["usedTimes"] == 0
    assert first.json()["transaction"]["txnType"] == "adjust"
    assert first.json()["transaction"]["timesDelta"] == 3
    assert first.json()["transaction"]["reason"] == "人工补偿"

    transactions = db.scalars(
        select(CardTransaction).where(CardTransaction.txn_type == "adjust")
    ).all()
    assert len(transactions) == 1
    assert transactions[0].before_state["remaining_times"] == 10
    assert transactions[0].after_state["remaining_times"] == 13
    audit = db.scalars(select(AuditLog).where(AuditLog.action == "adjust")).one()
    assert audit.before_state["remaining_times"] == 10
    assert audit.after_state["remaining_times"] == 13
    assert audit.reason == "人工补偿"
    timeline = client.get(f"/members/{member['id']}/timeline", headers=auth_headers).json()["items"]
    adjustment = next(item for item in timeline if item["source"] == "transaction" and item["action"] == "adjust")
    assert adjustment["summary"] == "调整次数"

    stored_card = db.get(MemberCard, UUID(card["id"]))
    stored_card.status = "closed"
    db.flush()
    closed_adjustment = client.post(
        path,
        json={"timesDelta": -2, "reason": "闭卡盘点"},
        headers=_headers(auth_headers, "adjust-times-closed-01"),
    )
    assert closed_adjustment.status_code == 200
    assert closed_adjustment.json()["memberCard"]["status"] == "closed"
    assert closed_adjustment.json()["memberCard"]["remainingTimes"] == 11
    assert closed_adjustment.json()["memberCard"]["usedTimes"] == 0

    rejected = client.post(
        path,
        json={"timesDelta": -12, "reason": "不能透支"},
        headers=_headers(auth_headers, "adjust-times-negative-01"),
    )
    assert rejected.status_code == 409
    assert rejected.json()["detail"] == "调整后剩余次数不能小于 0"

    listed = client.get("/members", headers=auth_headers).json()["items"]
    summary = next(item for item in listed if item["id"] == member["id"])["cardSummaries"]
    detail_summary = client.get(f"/members/{member['id']}", headers=auth_headers).json()["cardSummaries"]
    assert summary == detail_summary
    assert summary[0] == {
        "id": card["id"],
        "productName": "10次卡",
        "cardType": "times",
        "status": "closed",
        "remainingTimes": 11,
        "expiresOn": "2026-09-25",
    }


def test_adjust_times_rejects_non_count_card_and_invalid_payload(client, auth_headers):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    _, card = _purchase(client, auth_headers, "13800008102", card_type="duration")
    path = f"/member-cards/{card['id']}/adjust-times"

    non_count = client.post(
        path,
        json={"timesDelta": 1, "reason": "补偿"},
        headers=_headers(auth_headers, "adjust-duration-card-01"),
    )
    assert non_count.status_code == 409
    assert non_count.json()["detail"] == "仅计次卡可调整剩余次数"

    for payload, message in (
        ({"timesDelta": 0, "reason": "补偿"}, "timesDelta 不能为 0"),
        ({"timesDelta": "1", "reason": "补偿"}, "timesDelta 必须是整数"),
        ({"timesDelta": 1, "reason": "   "}, "reason 不能为空"),
    ):
        response = client.post(
            path,
            json=payload,
            headers=_headers(auth_headers, f"invalid-adjust-{len(message)}"),
        )
        assert response.status_code == 422
        assert message in str(response.json())


def test_member_summary_derives_expired_status_without_per_member_queries(client, auth_headers, db):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    member, card = _purchase(client, auth_headers, "13800008103")
    stored_card = db.get(MemberCard, UUID(card["id"]))
    stored_card.expires_on = TODAY - __import__("datetime").timedelta(days=1)
    stored_card.status = "active"
    db.flush()

    listed = client.get("/members", headers=auth_headers).json()["items"]
    summary = next(item for item in listed if item["id"] == member["id"])["cardSummaries"][0]
    assert summary["status"] == "expired"
    assert stored_card.status == "active"
