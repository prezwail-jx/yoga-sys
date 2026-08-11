from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, HttpUrl

from app.schemas.base import ApiModel


CourseDifficulty = Literal["all_levels", "beginner", "intermediate", "advanced"]


class CreateCourseRequest(ApiModel):
    name: str = Field(min_length=1, max_length=100)
    duration_minutes: int = Field(gt=0, le=480)
    difficulty: CourseDifficulty = "all_levels"
    description: str | None = Field(None, max_length=4000)
    cover_url: HttpUrl | None = None
    enabled: bool = True


class UpdateCourseRequest(ApiModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    duration_minutes: int | None = Field(None, gt=0, le=480)
    difficulty: CourseDifficulty | None = None
    description: str | None = Field(None, max_length=4000)
    cover_url: HttpUrl | None = None
    enabled: bool | None = None


class CourseResponse(ApiModel):
    id: UUID
    name: str
    duration_minutes: int
    difficulty: CourseDifficulty
    description: str | None
    cover_url: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class CourseListResponse(ApiModel):
    items: list[CourseResponse]
    total: int
    skip: int
    limit: int


class CreateRoomRequest(ApiModel):
    name: str = Field(min_length=1, max_length=100)
    capacity: int = Field(gt=0, le=500)
    enabled: bool = True


class UpdateRoomRequest(ApiModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    capacity: int | None = Field(None, gt=0, le=500)
    enabled: bool | None = None


class RoomResponse(ApiModel):
    id: UUID
    name: str
    capacity: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


class RoomListResponse(ApiModel):
    items: list[RoomResponse]
    total: int
    skip: int
    limit: int


class CreateCoachRequest(ApiModel):
    name: str = Field(min_length=1, max_length=50)
    avatar_url: HttpUrl | None = None
    bio: str | None = Field(None, max_length=4000)
    specialty_course_ids: list[UUID] | None = None
    enabled: bool = True


class UpdateCoachRequest(ApiModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    avatar_url: HttpUrl | None = None
    bio: str | None = Field(None, max_length=4000)
    specialty_course_ids: list[UUID] | None = None
    enabled: bool | None = None


class CoachResponse(ApiModel):
    id: UUID
    name: str
    avatar_url: str | None
    bio: str | None
    specialty_course_ids: list[UUID] | None
    enabled: bool
    created_at: datetime
    updated_at: datetime
    has_account: bool = False
    username: str | None = None
    account_id: UUID | None = None


class CoachListResponse(ApiModel):
    items: list[CoachResponse]
    total: int
    skip: int
    limit: int
