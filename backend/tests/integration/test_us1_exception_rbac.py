from sqlalchemy import select

from app.domain.audit_log import AuditLog


def test_coach_member_write_is_forbidden_and_audited(client, auth_headers, coach_headers, db):
    created = client.post(
        "/members",
        json={"name": "权限测试", "phone": "13500001234", "joinDate": "2026-07-15"},
        headers=auth_headers,
    )
    member_id = created.json()["id"]

    denied = client.patch(
        f"/members/{member_id}",
        json={"name": "越权修改"},
        headers=coach_headers,
    )
    assert denied.status_code == 403

    db.expire_all()
    audit = db.scalars(
        select(AuditLog)
        .where(AuditLog.operator_role == "coach", AuditLog.result == "rejected")
        .order_by(AuditLog.occurred_at.desc())
    ).first()
    assert audit is not None
    assert audit.object_id == member_id


def test_coach_card_product_write_is_forbidden(client, coach_headers):
    response = client.post(
        "/card-products",
        json={
            "name": "越权卡项",
            "cardType": "times",
            "price": 100,
            "totalTimes": 10,
            "activationMode": "immediate",
            "applicableCourseScope": "group",
        },
        headers=coach_headers,
    )
    assert response.status_code == 403
