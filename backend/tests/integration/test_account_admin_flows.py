import json

from sqlalchemy import select

from app.domain import AdminUser, AuditLog


def login_headers(client, username: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_member_account_status_reset_self_change_and_password_safe_audit(
    client, auth_headers, coach_headers, db
):
    member = client.post(
        "/members",
        json={"name": "Account Member", "phone": "13900008881", "joinDate": "2026-08-05"},
        headers=auth_headers,
    ).json()
    member_id = member["id"]

    detail = client.get(f"/members/{member_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["hasAccount"] is False
    assert detail.json()["username"] is None

    created = client.post(
        f"/members/{member_id}/account",
        json={"username": "account-member", "initialPassword": "old-password"},
        headers={**auth_headers, "Idempotency-Key": "account-member-create"},
    )
    assert created.status_code == 201

    listed = client.get("/members", headers=auth_headers).json()["items"]
    listed_member = next(item for item in listed if item["id"] == member_id)
    assert listed_member["hasAccount"] is True
    assert listed_member["username"] == "account-member"

    forbidden = client.post(
        f"/members/{member_id}/account/reset-password",
        json={"newPassword": "reset-password"},
        headers=coach_headers,
    )
    assert forbidden.status_code == 403
    reset = client.post(
        f"/members/{member_id}/account/reset-password",
        json={"newPassword": "reset-password"},
        headers=auth_headers,
    )
    assert reset.status_code == 204
    assert reset.content == b""
    assert client.post(
        "/auth/login", json={"username": "account-member", "password": "old-password"}
    ).status_code == 401

    member_headers = login_headers(client, "account-member", "reset-password")
    wrong_old = client.post(
        "/auth/change-password",
        json={"oldPassword": "wrong-password", "newPassword": "final-password"},
        headers=member_headers,
    )
    assert wrong_old.status_code == 401
    changed = client.post(
        "/auth/change-password",
        json={"oldPassword": "reset-password", "newPassword": "final-password"},
        headers=member_headers,
    )
    assert changed.status_code == 204
    assert client.post(
        "/auth/change-password",
        json={"oldPassword": "admin123", "newPassword": "other-password"},
        headers=auth_headers,
    ).status_code == 403
    assert client.post(
        "/auth/login", json={"username": "account-member", "password": "final-password"}
    ).status_code == 200

    audits = list(
        db.scalars(
            select(AuditLog).where(
                AuditLog.action.in_(
                    ["member_account_password_reset", "member_account_password_change"]
                )
            )
        ).all()
    )
    assert {audit.action for audit in audits} == {
        "member_account_password_reset",
        "member_account_password_change",
    }
    serialized = json.dumps([audit.after_state for audit in audits])
    assert "reset-password" not in serialized
    assert "final-password" not in serialized
    assert "passwordHash" not in serialized


def test_admin_resets_coach_password(client, auth_headers, db):
    coach = db.scalar(select(AdminUser).where(AdminUser.username == "coach"))
    response = client.post(
        f"/coaches/{coach.coach_profile_id}/account/reset-password",
        json={"newPassword": "new-coach-password"},
        headers=auth_headers,
    )
    assert response.status_code == 204
    assert client.post(
        "/auth/login", json={"username": "coach", "password": "coach123"}
    ).status_code == 401
    assert client.post(
        "/auth/login", json={"username": "coach", "password": "new-coach-password"}
    ).status_code == 200


def test_coach_changes_own_password_and_records_role_audit(client, auth_headers, db):
    coach_headers = login_headers(client, "coach", "coach123")
    wrong_old = client.post(
        "/auth/change-password",
        json={"oldPassword": "wrong-password", "newPassword": "final-coach-password"},
        headers=coach_headers,
    )
    assert wrong_old.status_code == 401
    changed = client.post(
        "/auth/change-password",
        json={"oldPassword": "coach123", "newPassword": "final-coach-password"},
        headers=coach_headers,
    )
    assert changed.status_code == 204
    assert client.post(
        "/auth/login", json={"username": "coach", "password": "coach123"}
    ).status_code == 401
    assert client.post(
        "/auth/login", json={"username": "coach", "password": "final-coach-password"}
    ).status_code == 200

    audits = list(
        db.scalars(
            select(AuditLog).where(
                AuditLog.action.in_(["coach_account_password_change"])
            )
        ).all()
    )
    assert {audit.action for audit in audits} == {"coach_account_password_change"}
    serialized = json.dumps([audit.after_state for audit in audits])
    assert "coach123" not in serialized
    assert "final-coach-password" not in serialized
    assert "passwordHash" not in serialized
