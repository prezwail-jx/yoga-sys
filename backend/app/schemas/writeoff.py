from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.base import ApiModel

WriteOffEventType = Literal["reserve_hold", "checkin_commit", "cancel_refund", "absence_commit"]
TimelineCategory = Literal["all", "transaction", "writeoff", "audit"]

class CreateWriteOffEventRequest(ApiModel):
    member_id: UUID
    business_ref: str = Field(min_length=1, max_length=128)
    event_type: WriteOffEventType

class WriteOffEventResponse(ApiModel):
    id: UUID
    member_id: UUID
    member_card_id: UUID
    previous_event_id: UUID | None
    event_type: WriteOffEventType
    business_ref: str
    sequence_no: int
    times_delta: int
    selection_basis: str
    idempotency_key: str
    trace_id: str
    operator_id: str
    operator_role: str
    occurred_at: datetime

class TimelineEventResponse(ApiModel):
    id: UUID
    source: Literal["transaction", "writeoff", "audit"]
    action: str
    result: Literal["success", "rejected", "failed"]
    occurred_at: datetime
    trace_id: str
    member_card_id: UUID | None = None
    business_ref: str | None = None
    sequence_no: int | None = None
    times_delta: int | None = None
    amount: Decimal | None = None
    product_name: str | None = None
    card_type: str | None = None
    valid_days_delta: int | None = None
    reason: str | None = None
    operator_id: str | None = None
    operator_role: str | None = None
    object_type: str | None = None
    object_id: str | None = None
    summary: str

class TimelineListResponse(ApiModel):
    items: list[TimelineEventResponse]
    total: int
    skip: int
    limit: int
