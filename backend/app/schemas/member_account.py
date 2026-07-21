from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.base import ApiModel


class CreateMemberAccountRequest(ApiModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    initial_password: str = Field(min_length=8, max_length=128)


class MemberAccountResponse(ApiModel):
    id: UUID
    username: str
    role: Literal["member"]
    member_id: UUID
    created_at: datetime
