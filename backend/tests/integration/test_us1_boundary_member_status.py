import pytest
from fastapi import HTTPException

from app.repositories.member import MemberRepository
from app.services.member import MemberService


def test_disabled_member_is_rejected_by_booking_guard(client, auth_headers, db):
    created = client.post(
        "/members",
        json={"name": "周宁", "phone": "13900004567", "joinDate": "2026-07-15"},
        headers=auth_headers,
    )
    member_id = created.json()["id"]
    disabled = client.patch(
        f"/members/{member_id}",
        json={"status": "disabled"},
        headers=auth_headers,
    )
    assert disabled.status_code == 200

    with pytest.raises(HTTPException) as error:
        MemberService(MemberRepository(db)).ensure_bookable(member_id)
    assert error.value.status_code == 409


def test_admin_can_return_disabled_member_to_normal(client, auth_headers):
    created = client.post(
        "/members",
        json={"name": "陈悦", "phone": "13700007890", "joinDate": "2026-07-15"},
        headers=auth_headers,
    )
    member_id = created.json()["id"]
    assert client.patch(f"/members/{member_id}", json={"status": "disabled"}, headers=auth_headers).status_code == 200
    response = client.patch(f"/members/{member_id}", json={"status": "normal"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "normal"


def test_soft_deleted_phone_cannot_be_reused(client, auth_headers):
    payload = {"name": "赵敏", "phone": "13600001234", "joinDate": "2026-07-15"}
    created = client.post("/members", json=payload, headers=auth_headers)
    member_id = created.json()["id"]
    assert client.delete(f"/members/{member_id}", headers=auth_headers).status_code == 204
    assert client.get(f"/members/{member_id}", headers=auth_headers).status_code == 404
    duplicate = client.post("/members", json=payload, headers=auth_headers)
    assert duplicate.status_code == 409
