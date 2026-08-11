from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.base import ApiModel

CardStatus = Literal["pending_activation", "active", "frozen", "expired", "closed"]
TransactionType = Literal["purchase", "renew", "reissue", "refund", "freeze", "unfreeze", "extend"]

class MemberCardResponse(ApiModel):
    id: UUID
    member_id: UUID
    card_product_id: UUID
    source_member_card_id: UUID | None
    product_name: str
    card_type: str
    status: CardStatus
    remaining_times: int | None
    used_times: int
    valid_days: int | None
    opened_on: date | None
    expires_on: date | None
    remind_on: date | None
    frozen_from: date | None
    frozen_until: date | None
    freeze_reason: str | None
    total_frozen_days: int
    expiring_soon: bool = False
    terms_snapshot: dict[str, Any]
    refundable_transaction_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

class MemberCardListResponse(ApiModel):
    items: list[MemberCardResponse]
    total: int

class CardTransactionResponse(ApiModel):
    id: UUID
    member_id: UUID
    member_card_id: UUID
    origin_transaction_id: UUID | None
    source_member_card_id: UUID | None
    txn_type: TransactionType
    amount: Decimal | None
    times_delta: int | None
    valid_days_delta: int | None
    reason: str | None
    idempotency_key: str
    trace_id: str
    operator_id: str
    operator_role: str
    occurred_at: datetime

class TransactionOperationResponse(ApiModel):
    transaction: CardTransactionResponse
    member_card: MemberCardResponse

class CreateTransactionRequest(ApiModel):
    txn_type: Literal["purchase", "renew", "reissue", "refund", "extend"]
    member_id: UUID
    card_product_id: UUID | None = None
    member_card_id: UUID | None = None
    origin_transaction_id: UUID | None = None
    valid_days_delta: int | None = Field(None, ge=1)
    reason: str | None = Field(None, max_length=255)

    @model_validator(mode="after")
    def validate_shape(self):
        if self.txn_type == "purchase":
            if self.card_product_id is None or self.member_card_id is not None:
                raise ValueError("purchase requires cardProductId only")
        else:
            if self.member_card_id is None:
                raise ValueError(f"{self.txn_type} requires memberCardId")
        if self.txn_type == "refund" and self.origin_transaction_id is None:
            raise ValueError("refund requires originTransactionId")
        if self.txn_type == "extend" and self.valid_days_delta is None:
            raise ValueError("extend requires validDaysDelta")
        return self

class MemberSelfCardResponse(ApiModel):
    """Read-only card view for member self-service (Mini Program).

    MUST NOT expose: member_id, card_product_id, source_member_card_id,
    refundable_transaction_id, used_times, valid_days, remind_on,
    freeze_reason, total_frozen_days, expiring_soon, terms_snapshot,
    created_at, updated_at, or any lifecycle/audit field.
    """
    id: UUID
    product_name: str
    card_type: str
    status: CardStatus
    remaining_times: int | None
    opened_on: date | None
    expires_on: date | None
    frozen_from: date | None
    frozen_until: date | None


class MemberSelfCardListResponse(ApiModel):
    items: list[MemberSelfCardResponse]
    total: int


class FreezeMemberCardRequest(ApiModel):
    frozen_until: date
    reason: str = Field(min_length=1, max_length=255)

class UnfreezeMemberCardRequest(ApiModel):
    reason: str | None = Field(None, max_length=255)
