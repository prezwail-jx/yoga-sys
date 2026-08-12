from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.audit import record_audit
from app.api.deps import CurrentUser, get_current_user
from app.infra.db.session import get_session
from app.infra.observability import business_span
from app.repositories.member import MemberRepository
from app.schemas.writeoff import TimelineListResponse
from app.services.access_policy_service import AccessPolicyService
from app.services.member_timeline_service import MemberTimelineService

router = APIRouter()

@router.get("/members/{memberId}/timeline", response_model=TimelineListResponse)
def get_member_timeline(
    memberId: UUID,
    request: Request,
    category: Literal["all", "transaction", "writeoff", "audit"] = "all",
    action: str | None = None,
    date_from: date | None = Query(None, alias="dateFrom"),
    date_to: date | None = Query(None, alias="dateTo"),
    business_ref: str | None = Query(None, alias="businessRef", max_length=128),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="dateFrom 必须不晚于 dateTo")
    member = MemberRepository(session).get_by_id(memberId)
    if not member:
        raise HTTPException(status_code=404, detail="会员不存在")
    try:
        AccessPolicyService().assert_member_readable(user, str(memberId))
    except HTTPException:
        record_audit(
            session, trace_id=request.state.trace_id, action="read_timeline", user=user,
            object_type="member_timeline", object_id=str(memberId), member_id=memberId,
            result="rejected", reason="Cross-member timeline access denied",
        )
        session.commit()
        raise
    with business_span("member_timeline.query", member_id=memberId, category=category, actor_role=user.role):
        items, total = MemberTimelineService(session).query(
            member_id=memberId, actor_role=user.role, category=category, action=action,
            date_from=date_from, date_to=date_to, business_ref=business_ref, skip=skip, limit=limit,
        )
    return {"items": items, "total": total, "skip": skip, "limit": limit}
