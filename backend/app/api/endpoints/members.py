from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.audit import record_audit
from app.api.deps import CurrentUser, get_current_admin, get_member_service
from app.api.deps.business_clock import get_business_today
from app.infra.db.session import get_session
from app.schemas.member import (
    CreateMemberRequest,
    MemberListResponse,
    MemberResponse,
    MemberStatusEnum,
    UpdateMemberRequest,
)
from app.services.member import MemberService

router = APIRouter()


def state(member) -> dict:
    return MemberResponse.model_validate(member).model_dump(mode="json", by_alias=True)


@router.post("", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def create_member(
    payload: CreateMemberRequest,
    request: Request,
    service: MemberService = Depends(get_member_service),
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_admin),
):
    member = service.create_member(payload)
    record_audit(
        session,
        trace_id=request.state.trace_id,
        action="member_create",
        user=user,
        object_type="member",
        object_id=str(member.id),
        member_id=member.id,
        after_state=state(member),
    )
    return member


@router.get("", response_model=MemberListResponse)
def list_members(
    keyword: str | None = None,
    member_status: MemberStatusEnum | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: MemberService = Depends(get_member_service),
    today=Depends(get_business_today),
    _: CurrentUser = Depends(get_current_admin),
):
    items, total = service.list_members(skip, limit, keyword, member_status, today)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{memberId}", response_model=MemberResponse)
def get_member(
    memberId: UUID,
    service: MemberService = Depends(get_member_service),
    today=Depends(get_business_today),
    _: CurrentUser = Depends(get_current_admin),
):
    return service.get_member_response(memberId, today)


@router.patch("/{memberId}", response_model=MemberResponse)
def update_member(
    memberId: UUID,
    payload: UpdateMemberRequest,
    request: Request,
    service: MemberService = Depends(get_member_service),
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_admin),
):
    before = state(service.get_member(memberId))
    member = service.update_member(memberId, payload)
    record_audit(
        session,
        trace_id=request.state.trace_id,
        action="member_update",
        user=user,
        object_type="member",
        object_id=str(member.id),
        member_id=member.id,
        before_state=before,
        after_state=state(member),
    )
    return member


@router.delete("/{memberId}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    memberId: UUID,
    request: Request,
    service: MemberService = Depends(get_member_service),
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_admin),
):
    before = state(service.get_member(memberId))
    member = service.delete_member(memberId)
    record_audit(
        session,
        trace_id=request.state.trace_id,
        action="member_delete",
        user=user,
        object_type="member",
        object_id=str(member.id),
        member_id=member.id,
        before_state=before,
        after_state=state(member),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
