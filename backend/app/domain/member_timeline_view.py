from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

@dataclass(slots=True)
class MemberTimelineView:
    id: UUID
    source: str
    action: str
    result: str
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
    summary: str = ""
