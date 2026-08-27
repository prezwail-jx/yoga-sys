from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException

from app.api.audit import record_audit
from app.api.deps.auth import CurrentUser
from app.domain.member_card import MemberCard
from app.repositories.card_product import CardProductRepository
from app.repositories.member import MemberRepository
from app.repositories.member_card_repository import MemberCardRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.member_card import CreateTransactionRequest
from app.services.transaction_service import TransactionService, card_state

SYSTEM_USER = CurrentUser(user_id="system", role="system")

class MemberCardLifecycleService:
    def __init__(self, session, member_repo: MemberRepository, product_repo: CardProductRepository, card_repo: MemberCardRepository, transaction_repo: TransactionRepository):
        self.session, self.member_repo, self.card_repo, self.transaction_repo = session, member_repo, card_repo, transaction_repo
        self.transactions = TransactionService(session, member_repo, product_repo, card_repo, transaction_repo)

    def _card(self, card_id: UUID, *, member_id: UUID | None = None) -> MemberCard:
        card = self.card_repo.get_by_id(card_id, for_update=True)
        if not card or (member_id is not None and card.member_id != member_id):
            raise HTTPException(status_code=404, detail="会员卡不存在")
        return card

    def _unfreeze(self, card: MemberCard, *, today: date, user: CurrentUser, key: str, trace_id: str, reason: str | None):
        if card.status != "frozen" or card.frozen_from is None:
            raise HTTPException(status_code=409, detail="仅冻结中的卡可解冻")
        before = card_state(card)
        frozen_days = max(1, (today - card.frozen_from).days)
        if card.expires_on:
            card.expires_on += timedelta(days=frozen_days)
            card.remind_on = card.expires_on - timedelta(days=7)
        card.status, card.total_frozen_days = "active", card.total_frozen_days + frozen_days
        card.frozen_from = card.frozen_until = None
        card.freeze_reason = None
        self.card_repo.update(card)
        transaction = self.transactions._transaction(txn_type="unfreeze", card=card, user=user, key=key, trace_id=trace_id, before=before, amount=Decimal("0.00"), valid_days_delta=frozen_days, reason=reason)
        return transaction, card

    def reconcile_card(self, card: MemberCard, today: date, trace_id: str = "lifecycle-reconcile") -> MemberCard:
        if card.status == "frozen" and card.frozen_until and today >= card.frozen_until:
            self._unfreeze(card, today=card.frozen_until, user=SYSTEM_USER, key=f"auto-unfreeze:{card.id}:{card.frozen_until}", trace_id=trace_id, reason="冻结截止日自动解冻")
        if card.status == "active" and card.expires_on and today > card.expires_on:
            before = card_state(card)
            card.status = "expired"
            self.card_repo.update(card)
            record_audit(self.session, trace_id=trace_id, idempotency_key=f"auto-expire:{card.id}:{card.expires_on}", action="expire", user=SYSTEM_USER, object_type="member_card", object_id=str(card.id), member_id=card.member_id, before_state=before, after_state=card_state(card), reason="访问时到期校准")
        return card

    def list_member_cards(self, member_id: UUID, today: date, trace_id: str) -> list[MemberCard]:
        if not self.member_repo.get_by_id(member_id):
            raise HTTPException(status_code=404, detail="会员不存在")
        cards = self.card_repo.list_by_member(member_id)
        return [self.reconcile_card(card, today, trace_id) for card in cards]

    def freeze(self, card_id: UUID, frozen_until: date, reason: str, today: date, user: CurrentUser, key: str, trace_id: str):
        card = self.reconcile_card(self._card(card_id), today, trace_id)
        if card.status != "active":
            raise HTTPException(status_code=409, detail="仅使用中的卡可冻结")
        if frozen_until <= today:
            raise HTTPException(status_code=422, detail="frozenUntil 必须晚于今天")
        before = card_state(card)
        card.status, card.frozen_from, card.frozen_until = "frozen", today, frozen_until
        card.freeze_reason = reason
        self.card_repo.update(card)
        transaction = self.transactions._transaction(txn_type="freeze", card=card, user=user, key=key, trace_id=trace_id, before=before, amount=Decimal("0.00"), reason=reason)
        return transaction, card

    def unfreeze(self, card_id: UUID, today: date, user: CurrentUser, key: str, trace_id: str, reason: str | None):
        return self._unfreeze(self._card(card_id), today=today, user=user, key=key, trace_id=trace_id, reason=reason)

    def adjust_times(self, card_id: UUID, times_delta: int, reason: str, user: CurrentUser, key: str, trace_id: str):
        card = self._card(card_id)
        if card.remaining_times is None:
            raise HTTPException(status_code=409, detail="仅计次卡可调整剩余次数")
        remaining_times = card.remaining_times + times_delta
        if remaining_times < 0:
            raise HTTPException(status_code=409, detail="调整后剩余次数不能小于 0")
        before = card_state(card)
        card.remaining_times = remaining_times
        self.card_repo.update(card)
        transaction = self.transactions._transaction(
            txn_type="adjust", card=card, user=user, key=key, trace_id=trace_id,
            before=before, amount=Decimal("0.00"), times_delta=times_delta, reason=reason,
        )
        return transaction, card

    def extend(self, request: CreateTransactionRequest, today: date, user: CurrentUser, key: str, trace_id: str):
        self.transactions._member(request.member_id)
        card = self.reconcile_card(self._card(request.member_card_id, member_id=request.member_id), today, trace_id)
        if card.status not in {"pending_activation", "active", "frozen"}:
            raise HTTPException(status_code=409, detail="当前卡状态不能延期")
        before, days = card_state(card), int(request.valid_days_delta)
        card.valid_days = (card.valid_days or 0) + days
        if card.expires_on:
            card.expires_on += timedelta(days=days)
            card.remind_on = card.expires_on - timedelta(days=7)
        self.card_repo.update(card)
        transaction = self.transactions._transaction(txn_type="extend", card=card, user=user, key=key, trace_id=trace_id, before=before, amount=Decimal("0.00"), valid_days_delta=days, reason=request.reason)
        return transaction, card
