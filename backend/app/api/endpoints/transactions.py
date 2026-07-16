from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_admin
from app.api.deps.business_clock import get_business_today
from app.infra.db.session import get_session
from app.repositories.card_product import CardProductRepository
from app.repositories.member import MemberRepository
from app.repositories.member_card_repository import MemberCardRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.member_card import CreateTransactionRequest, MemberCardResponse, TransactionOperationResponse
from app.services.idempotency_service import IdempotencyConflictError, IdempotencyService
from app.services.member_card_lifecycle_service import MemberCardLifecycleService
from app.services.transaction_service import TransactionService

router = APIRouter()

def operation_body(transaction, card, today):
    refundable = transaction.id if transaction.txn_type in {"purchase", "renew"} else None
    card_data = MemberCardResponse.model_validate(card).model_copy(update={"expiring_soon": card.status == "active" and card.remind_on is not None and card.remind_on <= today <= card.expires_on, "refundable_transaction_id": refundable})
    return TransactionOperationResponse(transaction=transaction, member_card=card_data).model_dump(mode="json", by_alias=True)

@router.post("/transactions")
def create_transaction(payload: CreateTransactionRequest, request: Request, idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128), session: Session = Depends(get_session), user: CurrentUser = Depends(get_current_admin), today=Depends(get_business_today)):
    idempotency = IdempotencyService(session)
    request_body = payload.model_dump(mode="json", exclude_none=True)
    request_hash = idempotency.compute_request_hash(request_body)
    idempotency.acquire(scope="transactions", actor_id=user.user_id, idempotency_key=idempotency_key)
    try:
        replay = idempotency.check(scope="transactions", actor_id=user.user_id, idempotency_key=idempotency_key, request_hash=request_hash)
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if replay.hit:
        return JSONResponse(status_code=replay.response_code, content=replay.response_body)
    card_repo, transaction_repo = MemberCardRepository(session), TransactionRepository(session)
    member_repo, product_repo = MemberRepository(session), CardProductRepository(session)
    service = TransactionService(session, member_repo, product_repo, card_repo, transaction_repo)
    lifecycle = MemberCardLifecycleService(session, member_repo, product_repo, card_repo, transaction_repo)
    trace_id = request.state.trace_id
    if payload.txn_type == "purchase":
        transaction, card = service.purchase(payload, user, idempotency_key, trace_id, today)
    else:
        card = lifecycle.reconcile_card(service._card(payload.member_id, payload.member_card_id), today, trace_id)
        if payload.txn_type == "renew":
            transaction, card = service.renew(payload, user, idempotency_key, trace_id, today)
        elif payload.txn_type == "reissue":
            transaction, card = service.reissue(payload, user, idempotency_key, trace_id)
        elif payload.txn_type == "refund":
            transaction, card = service.refund(payload, user, idempotency_key, trace_id, today)
        else:
            transaction, card = lifecycle.extend(payload, today, user, idempotency_key, trace_id)
    body = operation_body(transaction, card, today)
    idempotency.persist(scope="transactions", actor_id=user.user_id, idempotency_key=idempotency_key, request_hash=request_hash, response_code=200, response_body=body)
    return body
