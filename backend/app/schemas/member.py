from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.base import ApiModel

MemberStatusEnum = Literal["normal", "paused", "expired", "disabled"]
CardStatusEnum = Literal["pending_activation", "active", "frozen", "expired", "closed"]


class CreateMemberRequest(ApiModel):
    name: str = Field(min_length=1, max_length=50)
    phone: str = Field(min_length=1, max_length=20, pattern=r"^[0-9+ -]{6,20}$")
    join_date: date
    gender: Literal["male", "female", "other", "unknown"] | None = None
    birthday: date | None = None
    note: str | None = None
    emergency_contact: str | None = Field(None, max_length=100)


class UpdateMemberRequest(ApiModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    status: MemberStatusEnum | None = None
    gender: Literal["male", "female", "other", "unknown"] | None = None
    birthday: date | None = None
    note: str | None = None
    emergency_contact: str | None = Field(None, max_length=100)


class MemberCardSummary(ApiModel):
    id: UUID
    product_name: str
    card_type: str
    status: CardStatusEnum
    remaining_times: int | None
    expires_on: date | None


class MemberResponse(ApiModel):
    id: UUID
    name: str
    phone: str
    gender: str | None
    status: MemberStatusEnum
    join_date: date
    birthday: date | None
    note: str | None
    emergency_contact: str | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    has_account: bool = False
    username: str | None = None
    account_id: UUID | None = None
    card_summaries: list[MemberCardSummary] = Field(default_factory=list)


class MemberListResponse(ApiModel):
    items: list[MemberResponse]
    total: int
    skip: int
    limit: int
