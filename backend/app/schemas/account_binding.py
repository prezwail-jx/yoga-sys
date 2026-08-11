from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.base import ApiModel


class CreateAccountBindingRequest(ApiModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9_.-]+$")
    initial_password: str = Field(min_length=8, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class AccountBindingResponse(ApiModel):
    id: UUID
    username: str
    role: Literal["member", "coach"]
    member_id: UUID | None = None
    coach_profile_id: UUID | None = None
    created_at: datetime


class ResetPasswordRequest(ApiModel):
    new_password: str = Field(min_length=8, max_length=128)


class WechatBindingStatusResponse(ApiModel):
    account_id: UUID
    bound: bool
    bound_at: datetime | None = None


class UnbindConfirmationRequest(ApiModel):
    confirm: Literal[True]
