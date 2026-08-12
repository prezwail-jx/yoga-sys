from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.audit import record_audit
from app.api.deps import CurrentUser, get_current_admin, get_current_user
from app.api.deps.business_clock import get_business_today
from app.api.endpoints.transactions import operation_body
from app.infra.db.session import get_session
from app.infra.observability import business_span
from app.repositories.card_product import CardProductRepository
from app.repositories.member import MemberRepository
from app.repositories.member_card_repository import MemberCardRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.member_card import (
    FreezeMemberCardRequest,
    MemberCardListResponse,
    MemberCardResponse,
    MemberSelfCardListResponse,
    MemberSelfCardResponse,
    UnfreezeMemberCardRequest,
)
from app.services.idempotency_service import IdempotencyConflictError, IdempotencyService
from app.services.member_card_lifecycle_service import MemberCardLifecycleService

router = APIRouter()

def lifecycle_service(session):
    return MemberCardLifecycleService(session, MemberRepository(session), CardProductRepository(session), MemberCardRepository(session), TransactionRepository(session))

@router.get("/members/me/cards", response_model=MemberSelfCardListResponse)
def list_my_cards(
    request: Request,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
    today=Depends(get_business_today),
):
    if user.role != "member" or not user.member_id:
        raise HTTPException(status_code=403, detail="需要会员身份")
    member_id = UUID(user.member_id)
    cards = lifecycle_service(session).list_member_cards(member_id, today, request.state.trace_id)
    items = [MemberSelfCardResponse.model_validate(card) for card in cards]
    return {"items": items, "total": len(items)}


def _assert_admin_or_record_denial(
    session: Session,
    user: CurrentUser,
    target_member_id: UUID,
    trace_id: str,
) -> None:
    if user.role == "admin":
        return
    is_cross_member_access = (
        user.role == "member" and user.member_id != str(target_member_id)
    )
    record_audit(
        session,
        trace_id=trace_id,
        action="read_member_cards",
        user=user,
        object_type="member_cards",
        object_id=str(target_member_id),
        member_id=target_member_id,
        result="rejected",
        reason=(
            "Cross-member card list access denied"
            if is_cross_member_access
            else "Administrator card list access denied"
        ),
    )
    session.commit()
    raise HTTPException(status_code=403, detail="没有权限")


@router.get("/members/{memberId}/cards", response_model=MemberCardListResponse)
def list_member_cards(
    memberId: UUID,
    request: Request,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
    today=Depends(get_business_today),
):
    _assert_admin_or_record_denial(session, user, memberId, request.state.trace_id)
    cards = lifecycle_service(session).list_member_cards(memberId, today, request.state.trace_id)
    repo = TransactionRepository(session)
    items = [MemberCardResponse.model_validate(card).model_copy(update={"expiring_soon": card.status == "active" and card.remind_on is not None and card.remind_on <= today <= card.expires_on, "refundable_transaction_id": (candidate.id if (candidate := repo.latest_refundable_for_card(card.id)) else None)}) for card in cards]
    return {"items": items, "total": len(items)}

def _run_idempotent(scope, memberCardId, payload, request, key, session, user, today, action):
    service = IdempotencyService(session)
    body = payload.model_dump(mode="json", exclude_none=True)
    request_hash = service.compute_request_hash(body)
    service.acquire(scope=scope, actor_id=user.user_id, idempotency_key=key)
    try:
        replay = service.check(scope=scope, actor_id=user.user_id, idempotency_key=key, request_hash=request_hash)
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if replay.hit:
        return JSONResponse(status_code=replay.response_code, content=replay.response_body)
    lifecycle = lifecycle_service(session)
    with business_span("member_card.lifecycle", business_action=scope, member_card_id=memberCardId, actor_role=user.role):
        transaction, card = action(lifecycle)
    response = operation_body(transaction, card, today)
    service.persist(scope=scope, actor_id=user.user_id, idempotency_key=key, request_hash=request_hash, response_code=200, response_body=response)
    return response

@router.post("/member-cards/{memberCardId}/freeze")
def freeze_card(memberCardId: UUID, payload: FreezeMemberCardRequest, request: Request, idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128), session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin), today=Depends(get_business_today)):
    return _run_idempotent("member-card-freeze", memberCardId, payload, request, idempotency_key, session, user, today, lambda lifecycle: lifecycle.freeze(memberCardId, payload.frozen_until, payload.reason, today, user, idempotency_key, request.state.trace_id))

@router.post("/member-cards/{memberCardId}/unfreeze")
def unfreeze_card(memberCardId: UUID, payload: UnfreezeMemberCardRequest, request: Request, idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128), session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin), today=Depends(get_business_today)):
    return _run_idempotent("member-card-unfreeze", memberCardId, payload, request, idempotency_key, session, user, today, lambda lifecycle: lifecycle.unfreeze(memberCardId, today, user, idempotency_key, request.state.trace_id, payload.reason))
