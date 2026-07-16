from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.card_transaction import CardTransaction

class TransactionRepository:
    def __init__(self, session: Session):
        self.session = session

    def acquire_idempotency_lock(self, scope: str, actor_id: str, key: str) -> None:
        lock_key = f"{scope}:{actor_id}:{key}"
        self.session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"), {"lock_key": lock_key})

    def create(self, transaction: CardTransaction) -> CardTransaction:
        self.session.add(transaction)
        self.session.flush()
        self.session.refresh(transaction)
        return transaction

    def get_by_id(self, transaction_id: UUID, *, for_update: bool = False) -> CardTransaction | None:
        stmt = select(CardTransaction).where(CardTransaction.id == transaction_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.scalars(stmt).first()

    def find_by_idempotency(self, actor_id: str, key: str) -> CardTransaction | None:
        return self.session.scalars(select(CardTransaction).where(CardTransaction.operator_id == actor_id, CardTransaction.idempotency_key == key)).first()

    def has_later_transaction(self, transaction: CardTransaction) -> bool:
        stmt = select(CardTransaction.id).where(
            CardTransaction.member_card_id == transaction.member_card_id,
            CardTransaction.created_at > transaction.created_at,
            CardTransaction.txn_type != "refund",
        ).limit(1)
        return self.session.scalar(stmt) is not None

    def latest_refundable_for_card(self, card_id: UUID) -> CardTransaction | None:
        candidates = self.session.scalars(select(CardTransaction).where(CardTransaction.member_card_id == card_id, CardTransaction.txn_type.in_(("purchase", "renew"))).order_by(CardTransaction.created_at.desc())).all()
        for candidate in candidates:
            if not self.has_refund(candidate.id) and not self.has_later_transaction(candidate):
                return candidate
        return None

    def has_refund(self, origin_transaction_id: UUID) -> bool:
        return self.session.scalar(select(CardTransaction.id).where(CardTransaction.txn_type == "refund", CardTransaction.origin_transaction_id == origin_transaction_id).limit(1)) is not None
