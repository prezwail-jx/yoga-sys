from sqlalchemy import select
from app.core.security import create_access_token
from app.domain.audit_log import AuditLog
from .test_us3_normal_timeline import _member

def _member_headers(member_id: str) -> dict[str, str]:
    token = create_access_token({"sub": f"member:{member_id}", "role": "member", "memberId": member_id})
    return {"Authorization": f"Bearer {token}"}

def test_member_can_read_self_but_not_another_member_and_denial_is_audited(client, db, auth_headers):
    first = _member(client, auth_headers, "13800004801")
    second = _member(client, auth_headers, "13800004802")
    headers = _member_headers(first["id"])
    assert client.get(f"/members/{first['id']}/timeline", headers=headers).status_code == 200
    assert client.get(f"/members/{second['id']}/timeline", headers=headers).status_code == 403
    audit = db.scalars(select(AuditLog).where(AuditLog.member_id == second["id"], AuditLog.action == "read_timeline", AuditLog.result == "rejected")).first()
    assert audit is not None and audit.operator_role == "member"

def test_member_timeline_hides_internal_audit_and_operator_identifiers(client, auth_headers):
    member = _member(client, auth_headers, "13800004803")
    response = client.get(f"/members/{member['id']}/timeline", headers=_member_headers(member["id"]))
    assert response.status_code == 200
    assert all(item["source"] != "audit" for item in response.json()["items"])
    assert all(item.get("operatorId") is None for item in response.json()["items"])

def test_coach_cannot_read_member_timeline(client, coach_headers, auth_headers):
    member = _member(client, auth_headers, "13800004804")
    assert client.get(f"/members/{member['id']}/timeline", headers=coach_headers).status_code == 403
