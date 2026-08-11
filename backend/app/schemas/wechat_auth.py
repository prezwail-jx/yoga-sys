from __future__ import annotations

from pydantic import Field, field_validator

from app.schemas.base import ApiModel


class WechatSessionRequest(ApiModel):
    code: str = Field(min_length=1, max_length=512)


class WechatSessionResponse(ApiModel):
    state: str
    access_token: str | None = None
    token_type: str | None = None
    role: str | None = None
    binding_ticket: str | None = None
    expires_in: int | None = None
    error: str | None = None
    error_description: str | None = None


class WechatBindRequest(ApiModel):
    binding_ticket: str = Field(min_length=1, max_length=1024)
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class WechatBindResponse(ApiModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class WechatAuthErrorResponse(ApiModel):
    error: str
    error_description: str


class WechatErrorCode:
    CODE_INVALID = "wechat_code_invalid"
    PROVIDER_RATE_LIMITED = "wechat_provider_rate_limited"
    PROVIDER_UNAVAILABLE = "wechat_provider_unavailable"
    PROVIDER_TIMEOUT = "wechat_provider_timeout"
    PROVIDER_INVALID_RESPONSE = "wechat_provider_invalid_response"
    LOGIN_REJECTED = "wechat_login_rejected"
    ACCOUNT_DISABLED = "account_disabled"
    BINDING_CREDENTIALS_REJECTED = "binding_credentials_rejected"
    BINDING_CONFLICT = "wechat_binding_conflict"
    BINDING_ADMIN_FORBIDDEN = "binding_admin_forbidden"
    CHALLENGE_NOT_FOUND = "binding_challenge_not_found"
    CHALLENGE_EXPIRED = "binding_challenge_expired"
    CHALLENGE_CONSUMED = "binding_challenge_consumed"
    CHALLENGE_ATTEMPTS_EXCEEDED = "binding_challenge_attempts_exceeded"
    AUTH_DISABLED = "wechat_auth_disabled"
