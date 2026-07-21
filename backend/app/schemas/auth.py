from pydantic import BaseModel, Field, field_validator

from app.schemas.base import ApiModel

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class CurrentUserResponse(ApiModel):
    username: str
    role: str
    member_id: str | None = None
    coach_profile_id: str | None = None
