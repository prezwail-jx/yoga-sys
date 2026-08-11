from datetime import date, timedelta

from sqlalchemy import select

from app.core.security import create_access_token
from app.domain.audit_log import AuditLog
from app.domain.member import Member
from app.domain.member_card import MemberCard

TODAY = date(2026, 8, 6)

SELF_FIELDS = {"id", "productName", "cardType", "status",
               "remainingTimes", "openedOn", "expiresOn",
               "frozenFrom", "frozenUntil"}

def _member_headers(member_id: str) -> dict[str, str]:
    token = create_access_token(
        {"sub": f"member:{member_id}", "role": "member", "memberId": member_id}
    )
    return {"Authorization": f"Bearer {token}"}

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _member(client, admin_headers, phone, status="normal"):
    payload = {"name": "会员卡自助查询测试", "phone": phone,
               "joinDate": TODAY.isoformat()}
    res = client.post("/members", json=payload, headers=admin_headers)
    assert res.status_code == 201
    member = res.json()
    if status != "normal":
        res2 = client.patch(f"/members/{member['id']}",
                            json={"status": status}, headers=admin_headers)
        assert res2.status_code == 200
        member = res2.json()
    return member

def _product(client, admin_headers, name, card_type, **kw):
    payload = {"name": name, "cardType": card_type, "price": "100.00",
               "activationMode": "immediate", "applicableCourseScope": "group",
               "absenceDeductEnabled": True, "cancelRefundEnabled": True, **kw}
    res = client.post("/card-products", json=payload, headers=admin_headers)
    assert res.status_code == 201
    return res.json()

def _purchase(client, admin_headers, member_id, product_id, key):
    res = client.post("/transactions",
                      json={"txnType": "purchase", "memberId": member_id,
                            "cardProductId": product_id},
                      headers={"Idempotency-Key": key, **admin_headers})
    assert res.status_code == 200
    return res.json()["memberCard"]

def _freeze(client, admin_headers, card_id, key, until=None):
    until = until or (TODAY + timedelta(days=30)).isoformat()
    res = client.post(f"/member-cards/{card_id}/freeze",
                      json={"frozenUntil": until, "reason": "测试冻结"},
                      headers={"Idempotency-Key": key, **admin_headers})
    assert res.status_code == 200
    return res.json()["memberCard"]

# ---------------------------------------------------------------------------
# self-service card listing
# ---------------------------------------------------------------------------

def test_normal_member_retrieves_own_active_card(client, auth_headers):
    member = _member(client, auth_headers, "13800005501")
    product = _product(client, auth_headers, "自助-次卡", "times",
                       totalTimes=10, validDays=90)
    card = _purchase(client, auth_headers, member["id"], product["id"],
                     "ss-times-5501")

    headers = _member_headers(member["id"])
    res = client.get("/members/me/cards", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == card["id"]
    assert item["productName"] == "自助-次卡"
    assert item["cardType"] == "times"
    assert item["status"] == "active"
    assert item["remainingTimes"] == 10
    assert item["openedOn"] == TODAY.isoformat()
    assert item["expiresOn"] > TODAY.isoformat()
    assert item["frozenFrom"] is None
    assert item["frozenUntil"] is None
    assert set(item.keys()) == SELF_FIELDS


def test_paused_member_can_still_query_own_cards(client, auth_headers):
    member = _member(client, auth_headers, "13800005502", status="paused")
    product = _product(client, auth_headers, "自助-期限卡", "duration",
                       validDays=60)
    _purchase(client, auth_headers, member["id"], product["id"],
              "ss-dur-5502")

    res = client.get("/members/me/cards",
                     headers=_member_headers(member["id"]))
    assert res.status_code == 200
    assert res.json()["total"] == 1


def test_expired_member_can_still_query_own_cards(client, db, auth_headers):
    member = _member(client, auth_headers, "13800005503")
    m = db.scalars(select(Member).where(Member.id == member["id"])).first()
    m.status = "expired"
    db.flush()

    product = _product(client, auth_headers, "自助-次卡2", "times",
                       totalTimes=5, validDays=30)
    _purchase(client, auth_headers, member["id"], product["id"],
              "ss-ts-5503")

    res = client.get("/members/me/cards",
                     headers=_member_headers(member["id"]))
    assert res.status_code == 200
    assert res.json()["total"] == 1


def test_expired_card_reconciled_in_self_service(client, db, auth_headers):
    member = _member(client, auth_headers, "13800005504")
    product = _product(client, auth_headers, "自助-短效卡", "times",
                       totalTimes=3, validDays=1)
    card = _purchase(client, auth_headers, member["id"], product["id"],
                     "ss-short-5504")
    assert card["status"] == "active"

    card_obj = db.scalars(
        select(MemberCard).where(MemberCard.id == card["id"])
    ).first()
    card_obj.expires_on = TODAY - timedelta(days=1)
    card_obj.remind_on = TODAY - timedelta(days=2)
    db.flush()

    res = client.get("/members/me/cards",
                     headers=_member_headers(member["id"]))
    assert res.status_code == 200
    item = res.json()["items"][0]
    assert item["status"] == "expired"


def test_frozen_card_in_self_service(client, auth_headers):
    member = _member(client, auth_headers, "13800005505")
    product = _product(client, auth_headers, "自助-冻结卡", "times",
                       totalTimes=5, validDays=60)
    card = _purchase(client, auth_headers, member["id"], product["id"],
                     "ss-frz-5505")
    frozen = _freeze(client, auth_headers, card["id"], "ss-frz-act-5505")

    res = client.get("/members/me/cards",
                     headers=_member_headers(member["id"]))
    assert res.status_code == 200
    item = res.json()["items"][0]
    assert item["status"] == "frozen"
    assert item["frozenFrom"] == frozen["frozenFrom"]
    assert item["frozenUntil"] == frozen["frozenUntil"]


def test_duration_card_has_null_remaining_times(client, auth_headers):
    member = _member(client, auth_headers, "13800005506")
    product = _product(client, auth_headers, "自助-纯期限", "duration",
                       validDays=90)
    _purchase(client, auth_headers, member["id"], product["id"],
              "ss-dur2-5506")

    res = client.get("/members/me/cards",
                     headers=_member_headers(member["id"]))
    item = res.json()["items"][0]
    assert item["cardType"] == "duration"
    assert item["remainingTimes"] is None


def test_times_card_shows_remaining_times(client, auth_headers):
    member = _member(client, auth_headers, "13800005507")
    product = _product(client, auth_headers, "自助-20次", "times",
                       totalTimes=20, validDays=180)
    _purchase(client, auth_headers, member["id"], product["id"],
              "ss-20-5507")

    res = client.get("/members/me/cards",
                     headers=_member_headers(member["id"]))
    item = res.json()["items"][0]
    assert item["cardType"] == "times"
    assert item["remainingTimes"] == 20


def test_private_card_type_in_self_service(client, auth_headers):
    member = _member(client, auth_headers, "13800005508")
    product = _product(client, auth_headers, "自助-私教", "private",
                       totalTimes=10, validDays=180)
    _purchase(client, auth_headers, member["id"], product["id"],
              "ss-priv-5508")

    res = client.get("/members/me/cards",
                     headers=_member_headers(member["id"]))
    item = res.json()["items"][0]
    assert item["cardType"] == "private"
    assert item["remainingTimes"] == 10


def test_trial_card_type_in_self_service(client, auth_headers):
    member = _member(client, auth_headers, "13800005509")
    product = _product(client, auth_headers, "自助-体验卡", "trial",
                       totalTimes=1, validDays=30)
    _purchase(client, auth_headers, member["id"], product["id"],
              "ss-trial-5509")

    res = client.get("/members/me/cards",
                     headers=_member_headers(member["id"]))
    item = res.json()["items"][0]
    assert item["cardType"] == "trial"
    assert item["remainingTimes"] == 1
    assert item["expiresOn"] is not None


def test_empty_card_list_for_member_with_no_cards(client, auth_headers):
    member = _member(client, auth_headers, "13800005510")

    res = client.get("/members/me/cards",
                     headers=_member_headers(member["id"]))
    assert res.status_code == 200
    assert res.json() == {"items": [], "total": 0}


# ---------------------------------------------------------------------------
# cross-member isolation
# ---------------------------------------------------------------------------

def test_member_a_cannot_see_member_b_cards(client, auth_headers):
    member_a = _member(client, auth_headers, "13800005511")
    member_b = _member(client, auth_headers, "13800005512")
    product = _product(client, auth_headers, "隔离-次卡", "times",
                       totalTimes=5, validDays=30)
    _purchase(client, auth_headers, member_a["id"], product["id"],
              "ss-iso-a")
    _purchase(client, auth_headers, member_b["id"], product["id"],
              "ss-iso-b")

    res_a = client.get("/members/me/cards",
                       headers=_member_headers(member_a["id"]))
    assert res_a.status_code == 200
    assert res_a.json()["total"] == 1

    res_b = client.get("/members/me/cards",
                       headers=_member_headers(member_b["id"]))
    assert res_b.status_code == 200
    assert res_b.json()["total"] == 1

    assert res_a.json()["items"][0]["id"] != res_b.json()["items"][0]["id"]


def test_member_cannot_access_admin_card_list_route_for_other_member(
    client, db, auth_headers
):
    member_a = _member(client, auth_headers, "13800005513")
    member_b = _member(client, auth_headers, "13800005514")

    res = client.get(f"/members/{member_b['id']}/cards",
                     headers=_member_headers(member_a["id"]))
    assert res.status_code == 403

    audit = db.scalars(
        select(AuditLog).where(
            AuditLog.action == "read_member_cards",
            AuditLog.object_id == member_b["id"],
            AuditLog.result == "rejected",
        )
    ).first()
    assert audit is not None
    assert audit.operator_role == "member"
    assert audit.reason == "Cross-member card list access denied"


def test_member_accessing_own_admin_card_route_is_not_audited_as_cross_member(
    client, db, auth_headers
):
    member = _member(client, auth_headers, "13800005515")

    res = client.get(f"/members/{member['id']}/cards", headers=_member_headers(member["id"]))
    assert res.status_code == 403

    audit = db.scalars(
        select(AuditLog).where(
            AuditLog.action == "read_member_cards",
            AuditLog.object_id == member["id"],
            AuditLog.result == "rejected",
        )
    ).first()
    assert audit is not None
    assert audit.reason == "Administrator card list access denied"


# ---------------------------------------------------------------------------
# role rejection
# ---------------------------------------------------------------------------

def test_coach_cannot_access_self_service_cards(client, coach_headers):
    res = client.get("/members/me/cards", headers=coach_headers)
    assert res.status_code == 403


def test_admin_cannot_access_self_service_cards(client, auth_headers):
    res = client.get("/members/me/cards", headers=auth_headers)
    assert res.status_code == 403


def test_self_service_rejects_member_without_member_id_in_token(client):
    token = create_access_token({"sub": "no-memberid", "role": "member"})
    res = client.get("/members/me/cards", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


def test_self_service_rejects_member_with_malformed_member_id(client):
    token = create_access_token(
        {"sub": "bad-memberid", "role": "member", "memberId": "not-a-uuid"}
    )
    res = client.get("/members/me/cards", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# response field whitelist
# ---------------------------------------------------------------------------

def test_self_service_response_does_not_leak_admin_fields(client, auth_headers):
    FORBIDDEN = {
        "memberId", "cardProductId", "sourceMemberCardId",
        "refundableTransactionId", "usedTimes", "validDays", "remindOn",
        "freezeReason", "totalFrozenDays", "expiringSoon", "termsSnapshot",
        "createdAt", "updatedAt",
    }
    member = _member(client, auth_headers, "13800005518")
    product = _product(client, auth_headers, "字段白名单测试", "times",
                       totalTimes=8, validDays=60)
    _purchase(client, auth_headers, member["id"], product["id"],
              "ss-whitelist-5518")

    res = client.get("/members/me/cards",
                     headers=_member_headers(member["id"]))
    assert res.status_code == 200
    item = res.json()["items"][0]
    actual = set(item.keys())
    assert not actual.intersection(FORBIDDEN), \
        f"leaked forbidden fields: {actual & FORBIDDEN}"


# ---------------------------------------------------------------------------
# admin can still list member cards
# ---------------------------------------------------------------------------

def test_admin_can_still_list_member_cards(client, auth_headers):
    member = _member(client, auth_headers, "13800005519")
    product = _product(client, auth_headers, "管理员查卡", "times",
                       totalTimes=5, validDays=30)
    _purchase(client, auth_headers, member["id"], product["id"],
              "ss-admin-5519")

    res = client.get(f"/members/{member['id']}/cards", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["total"] == 1
    item = res.json()["items"][0]
    assert "refundableTransactionId" in item
    assert "usedTimes" in item


# ---------------------------------------------------------------------------
# coach also gets 403 + audit on admin card route
# ---------------------------------------------------------------------------

def test_coach_rejected_on_admin_card_list_and_audited(client, db, auth_headers,
                                                        coach_headers):
    member = _member(client, auth_headers, "13800005520")
    res = client.get(f"/members/{member['id']}/cards", headers=coach_headers)
    assert res.status_code == 403

    audit = db.scalars(
        select(AuditLog).where(
            AuditLog.action == "read_member_cards",
            AuditLog.object_id == member["id"],
            AuditLog.result == "rejected",
            AuditLog.operator_role == "coach",
        )
    ).first()
    assert audit is not None
