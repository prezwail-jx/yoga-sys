from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.base import ApiModel


ClassSessionStatus = Literal["draft", "published", "paused", "cancelled", "completed"]


class CreateClassSessionRequest(ApiModel):
    course_id: UUID
    coach_profile_id: UUID
    room_id: UUID
    start_at: datetime
    end_at: datetime
    capacity: int = Field(gt=0, le=500)
    booking_open_hours_before: int = Field(168, ge=0, le=24 * 365)
    booking_close_minutes_before: int = Field(0, ge=0, le=60 * 24 * 30)
    cancel_cutoff_minutes_before: int = Field(120, ge=0, le=60 * 24 * 30)

    @model_validator(mode="after")
    def validate_time_order(self):
        if self.end_at <= self.start_at:
            raise ValueError("endAt 必须晚于 startAt")
        return self


class UpdateClassSessionRequest(ApiModel):
    course_id: UUID | None = None
    coach_profile_id: UUID | None = None
    room_id: UUID | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    capacity: int | None = Field(None, gt=0, le=500)
    booking_open_hours_before: int | None = Field(None, ge=0, le=24 * 365)
    booking_close_minutes_before: int | None = Field(None, ge=0, le=60 * 24 * 30)
    cancel_cutoff_minutes_before: int | None = Field(None, ge=0, le=60 * 24 * 30)

    @model_validator(mode="after")
    def validate_time_order(self):
        if self.start_at is not None and self.end_at is not None and self.end_at <= self.start_at:
            raise ValueError("endAt 必须晚于 startAt")
        return self


class ClassSessionResponse(ApiModel):
    id: UUID
    course_id: UUID
    coach_profile_id: UUID
    room_id: UUID
    course_name: str
    coach_name: str
    room_name: str
    start_at: datetime
    end_at: datetime
    capacity: int
    booking_open_hours_before: int
    booking_close_minutes_before: int
    cancel_cutoff_minutes_before: int
    status: ClassSessionStatus
    source_session_id: UUID | None
    created_by: str
    booked_count: int
    remaining_capacity: int
    is_full: bool
    created_at: datetime
    updated_at: datetime


class ClassSessionListResponse(ApiModel):
    items: list[ClassSessionResponse]
    week_start: date
    week_end: date


class CopyWeekRequest(ApiModel):
    source_week_start: date
    target_week_start: date

    @model_validator(mode="after")
    def validate_distinct_weeks(self):
        if self.source_week_start == self.target_week_start:
            raise ValueError("sourceWeekStart 和 targetWeekStart 不能相同")
        return self


class CopyConflictResponse(ApiModel):
    source_session_id: UUID
    target_start_at: datetime
    reason: str


class CopyWeekResponse(ApiModel):
    created: list[ClassSessionResponse]
    conflicts: list[CopyConflictResponse]
