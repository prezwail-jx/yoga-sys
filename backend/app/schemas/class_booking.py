from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.base import ApiModel


ClassBookingStatus = Literal["reserved", "checked_in", "cancelled", "absent"]


class CreateClassBookingRequest(ApiModel):
    member_id: UUID | None = None


class CancelClassBookingRequest(ApiModel):
    reason: str | None = Field(None, max_length=255)


class ClassBookingResponse(ApiModel):
    id: UUID
    class_session_id: UUID
    member_id: UUID
    member_name: str
    course_name: str
    coach_name: str
    room_name: str
    start_at: datetime
    end_at: datetime
    session_status: Literal["draft", "published", "paused", "cancelled", "completed"]
    status: ClassBookingStatus
    booked_by_id: str | None
    booked_by_role: str | None
    booked_at: datetime
    terminal_by_id: str | None
    terminal_by_role: str | None
    terminal_at: datetime | None
    cancellation_reason: str | None
    trace_id: str
    created_at: datetime
    updated_at: datetime


class ClassBookingListResponse(ApiModel):
    items: list[ClassBookingResponse]
    total: int
    skip: int
    limit: int
