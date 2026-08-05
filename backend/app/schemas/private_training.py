from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.base import ApiModel


class PrivateAvailabilityInput(ApiModel):
    coach_profile_id: UUID | None = None
    start_at: datetime
    end_at: datetime

    @model_validator(mode="after")
    def validate_time_order(self):
        if self.end_at <= self.start_at:
            raise ValueError("endAt must be after startAt")
        return self


class PrivateAvailabilityWeekInput(ApiModel):
    coach_profile_id: UUID | None = None
    week_start: datetime
    weekdays: list[int] = Field(min_length=1, max_length=7)
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    duration_minutes: int = Field(gt=0, le=480)


class PrivateAvailabilityResponse(ApiModel):
    id: UUID
    coach_profile_id: UUID
    coach_name: str
    start_at: datetime
    end_at: datetime
    duration_minutes: int
    status: str
    created_by_id: str
    created_by_role: str
    created_at: datetime
    updated_at: datetime


class PrivateAvailabilityList(ApiModel):
    items: list[PrivateAvailabilityResponse]
    total: int


class PrivateAvailabilityConflict(ApiModel):
    start_at: datetime
    end_at: datetime
    reason: str


class PrivateAvailabilityWeekResult(ApiModel):
    created: list[PrivateAvailabilityResponse]
    conflicts: list[PrivateAvailabilityConflict]


class PrivateBookingInput(ApiModel):
    availability_id: UUID
    member_message: str | None = Field(default=None, max_length=500)


class PrivateBookingDecisionInput(ApiModel):
    reason: str | None = Field(default=None, max_length=255)


class PrivateLessonRecordInput(ApiModel):
    content: str = Field(min_length=1, max_length=5000)
    consumed_hours: Decimal = Field(gt=0, le=24)
    member_status_notes: str | None = Field(default=None, max_length=5000)


class PrivateBookingResponse(ApiModel):
    id: UUID
    availability_id: UUID
    member_id: UUID
    member_name: str
    coach_profile_id: UUID
    coach_name: str
    member_card_id: UUID | None
    start_at: datetime
    end_at: datetime
    duration_minutes: int
    status: str
    member_message: str | None
    rejection_reason: str | None
    cancellation_reason: str | None
    booked_by_id: str
    booked_by_role: str
    confirmed_at: datetime | None
    terminal_by_id: str | None
    terminal_by_role: str | None
    terminal_at: datetime | None
    trace_id: str
    created_at: datetime
    updated_at: datetime


class PrivateBookingList(ApiModel):
    items: list[PrivateBookingResponse]
    total: int
    skip: int
    limit: int


class PrivateLessonRecordResponse(ApiModel):
    id: UUID
    booking_id: UUID
    member_id: UUID
    coach_profile_id: UUID
    content: str
    consumed_hours: Decimal
    member_status_notes: str | None
    completed_at: datetime
    trace_id: str
    created_by_id: str
    created_by_role: str
    created_at: datetime
