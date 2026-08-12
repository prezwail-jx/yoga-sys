from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import HTTPException

from app.api.audit import record_audit
from app.domain.card_transaction import CardTransaction
from app.domain.member_card import MemberCard
from app.repositories.card_product import CardProductRepository
from app.repositories.member import MemberRepository
from app.repositories.member_card_repository import MemberCardRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.member_card import CreateTransactionRequest

if TYPE_CHECKING:
    from app.api.deps.auth import CurrentUser


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    return value

CARD_STATE_FIELDS = ("status", "remaining_times", "used_times", "valid_days", "opened_on", "expires_on", "remind_on", "frozen_from", "frozen_until", "freeze_reason", "total_frozen_days")

def card_state(card: MemberCard) -> dict[str, Any]:
    return {field: _json_value(getattr(card, field)) for field in CARD_STATE_FIELDS}

def restore_card_state(card: MemberCard, state: dict[str, Any]) -> None:
    date_fields = {"opened_on", "expires_on", "remind_on", "frozen_from", "frozen_until"}
    for field in CARD_STATE_FIELDS:
        value = state.get(field)
        if field in date_fields and value:
            value = date.fromisoformat(value)
        setattr(card, field, value)

def product_snapshot(product) -> dict[str, Any]:
    return {
        "productId": str(product.id), "name": product.name, "cardType": product.card_type,
        "price": str(product.price), "totalTimes": product.total_times, "validDays": product.valid_days,
        "activationMode": product.activation_mode, "applicableCourseScope": product.applicable_course_scope,
        "specificCourseIds": product.specific_course_ids, "absenceDeductEnabled": product.absence_deduct_enabled,
        "cancelRefundEnabled": product.cancel_refund_enabled,
    }

class TransactionService:
    def __init__(self, session, member_repo: MemberRepository, product_repo: CardProductRepository, card_repo: MemberCardRepository, transaction_repo: TransactionRepository):
        self.session, self.member_repo, self.product_repo = session, member_repo, product_repo
        self.card_repo, self.transaction_repo = card_repo, transaction_repo

    def _member(self, member_id: UUID):
        member = self.member_repo.get_by_id(member_id)
        if not member:
            raise HTTPException(status_code=404, detail="会员不存在")
        if member.status == "disabled":
            raise HTTPException(status_code=409, detail="停用会员不能办理卡项业务")
        return member

    def _card(self, member_id: UUID, card_id: UUID) -> MemberCard:
        card = self.card_repo.get_by_id(card_id, for_update=True)
        if not card or card.member_id != member_id:
            raise HTTPException(status_code=404, detail="会员卡不存在")
        return card

    def _transaction(self, *, txn_type: str, card: MemberCard, user: CurrentUser, key: str, trace_id: str, before: dict | None, amount: Decimal | None = None, times_delta: int | None = None, valid_days_delta: int | None = None, reason: str | None = None, origin_transaction_id: UUID | None = None, source_member_card_id: UUID | None = None) -> CardTransaction:
        transaction = self.transaction_repo.create(CardTransaction(
            member_id=card.member_id, member_card_id=card.id, origin_transaction_id=origin_transaction_id,
            source_member_card_id=source_member_card_id, txn_type=txn_type, amount=amount,
            times_delta=times_delta, valid_days_delta=valid_days_delta, reason=reason,
            idempotency_key=key, trace_id=trace_id, operator_id=user.user_id, operator_role=user.role,
            before_state=before, after_state=card_state(card),
        ))
        record_audit(self.session, trace_id=trace_id, idempotency_key=key, action=txn_type, user=user,
                     object_type="member_card", object_id=str(card.id), member_id=card.member_id,
                     before_state=before, after_state=card_state(card), reason=reason)
        return transaction

    def purchase(self, request: CreateTransactionRequest, user: CurrentUser, key: str, trace_id: str, today: date):
        member = self._member(request.member_id)
        product = self.product_repo.get_by_id(request.card_product_id)
        if not product or not product.enabled:
            raise HTTPException(status_code=404, detail="未找到启用的卡项产品")
        snapshot = product_snapshot(product)
        immediate = product.activation_mode == "immediate"
        expires_on = today + __import__("datetime").timedelta(days=product.valid_days - 1) if immediate and product.valid_days else None
        card = self.card_repo.create(MemberCard(
            member_id=member.id, card_product_id=product.id, status="active" if immediate else "pending_activation",
            product_name=product.name, card_type=product.card_type, terms_snapshot=snapshot,
            remaining_times=product.total_times, used_times=0, valid_days=product.valid_days,
            opened_on=today if immediate else None, expires_on=expires_on,
            remind_on=expires_on - __import__("datetime").timedelta(days=7) if expires_on else None,
            total_frozen_days=0,
        ))
        if member.status == "expired":
            member.status = "normal"
            self.member_repo.update(member)
        transaction = self._transaction(txn_type="purchase", card=card, user=user, key=key, trace_id=trace_id, before=None, amount=product.price, times_delta=product.total_times, valid_days_delta=product.valid_days)
        return transaction, card

    def renew(self, request: CreateTransactionRequest, user: CurrentUser, key: str, trace_id: str, today: date):
        member = self._member(request.member_id)
        card = self._card(member.id, request.member_card_id)
        if card.status == "closed":
            raise HTTPException(status_code=409, detail="已关闭的卡不能续费")
        before = card_state(card)
        times = card.terms_snapshot.get("totalTimes")
        days = card.terms_snapshot.get("validDays")
        if times:
            card.remaining_times = (card.remaining_times or 0) + int(times)
        if card.status == "pending_activation":
            card.valid_days = (card.valid_days or 0) + (int(days) if days else 0)
        elif card.status == "expired":
            card.status, card.opened_on = "active", today
            card.expires_on = today + __import__("datetime").timedelta(days=int(days) - 1) if days else None
        elif days and card.expires_on:
            card.expires_on += __import__("datetime").timedelta(days=int(days))
        if card.expires_on:
            card.remind_on = card.expires_on - __import__("datetime").timedelta(days=7)
        self.card_repo.update(card)
        if member.status == "expired":
            member.status = "normal"
            self.member_repo.update(member)
        transaction = self._transaction(txn_type="renew", card=card, user=user, key=key, trace_id=trace_id, before=before, amount=Decimal(str(card.terms_snapshot["price"])), times_delta=times, valid_days_delta=days)
        return transaction, card

    def reissue(self, request: CreateTransactionRequest, user: CurrentUser, key: str, trace_id: str):
        self._member(request.member_id)
        old = self._card(request.member_id, request.member_card_id)
        if old.status not in {"pending_activation", "active", "frozen"}:
            raise HTTPException(status_code=409, detail="当前卡状态不能补卡")
        before = card_state(old)
        new = self.card_repo.create(MemberCard(
            member_id=old.member_id, card_product_id=old.card_product_id, source_member_card_id=old.id,
            status=old.status, product_name=old.product_name, card_type=old.card_type,
            terms_snapshot=old.terms_snapshot, remaining_times=old.remaining_times, used_times=old.used_times,
            valid_days=old.valid_days, opened_on=old.opened_on, expires_on=old.expires_on, remind_on=old.remind_on,
            frozen_from=old.frozen_from, frozen_until=old.frozen_until, freeze_reason=old.freeze_reason,
            total_frozen_days=old.total_frozen_days,
        ))
        old.status, old.frozen_from, old.frozen_until = "closed", None, None
        self.card_repo.update(old)
        transaction = self._transaction(txn_type="reissue", card=new, user=user, key=key, trace_id=trace_id, before=before, amount=Decimal("0.00"), reason=request.reason, source_member_card_id=old.id)
        return transaction, new

    def refund(self, request: CreateTransactionRequest, user: CurrentUser, key: str, trace_id: str, today: date):
        self._member(request.member_id)
        card = self._card(request.member_id, request.member_card_id)
        origin = self.transaction_repo.get_by_id(request.origin_transaction_id, for_update=True)
        if not origin or origin.member_card_id != card.id or origin.txn_type not in {"purchase", "renew"}:
            raise HTTPException(status_code=404, detail="可退款的原始交易不存在")
        if self.transaction_repo.has_refund(origin.id) or self.transaction_repo.has_later_transaction(origin):
            raise HTTPException(status_code=409, detail="交易已退款或卡项之后已发生变化")
        if card_state(card) != origin.after_state:
            raise HTTPException(status_code=409, detail="卡项权益已被使用或变更")
        if origin.txn_type == "purchase" and card.card_type == "duration" and card.opened_on and card.opened_on < today:
            raise HTTPException(status_code=409, detail="已激活的期限卡已被使用")
        before = card_state(card)
        if origin.txn_type == "purchase":
            card.status = "closed"
        else:
            restore_card_state(card, origin.before_state or {})
        self.card_repo.update(card)
        transaction = self._transaction(txn_type="refund", card=card, user=user, key=key, trace_id=trace_id, before=before, amount=-origin.amount if origin.amount is not None else None, times_delta=-origin.times_delta if origin.times_delta else None, valid_days_delta=-origin.valid_days_delta if origin.valid_days_delta else None, reason=request.reason, origin_transaction_id=origin.id)
        return transaction, card
