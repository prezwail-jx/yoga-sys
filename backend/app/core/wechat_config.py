from __future__ import annotations

import os
import hmac
from functools import lru_cache
from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class WechatConfig:
    auth_enabled: bool
    provider: Literal["fake", "real"]
    app_id: str
    app_secret: str
    identity_pepper: str
    api_timeout_seconds: int
    binding_challenge_minutes: int
    binding_max_attempts: int
    binding_source_max_attempts: int
    binding_source_window_seconds: int
    source_fingerprint_pepper: str = field(repr=False)

    @classmethod
    def from_env(cls) -> WechatConfig:
        app_env = os.getenv("APP_ENV", "development")
        auth_enabled = os.getenv("WECHAT_AUTH_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
        provider_raw = os.getenv("WECHAT_PROVIDER", "fake").strip().lower()
        if provider_raw not in {"fake", "real"}:
            raise WechatConfigError(f"WECHAT_PROVIDER must be 'fake' or 'real', got '{provider_raw}'")
        provider: Literal["fake", "real"] = provider_raw  # type: ignore[assignment]

        app_id = os.getenv("WECHAT_APP_ID", "").strip()
        if auth_enabled and not app_id:
            raise WechatConfigError("WECHAT_APP_ID is required")
        if len(app_id) > 64:
            raise WechatConfigError("WECHAT_APP_ID exceeds 64 characters")

        app_secret = os.getenv("WECHAT_APP_SECRET", "").strip()
        identity_pepper = os.getenv("WECHAT_IDENTITY_PEPPER", "").strip()

        if app_env == "production" and provider == "fake":
            raise WechatConfigError("WECHAT_PROVIDER=fake is not allowed when APP_ENV=production")

        if auth_enabled and not identity_pepper:
            raise WechatConfigError("WECHAT_IDENTITY_PEPPER is required when WeChat authentication is enabled")
        jwt_secret = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "")).strip()
        if app_env == "production" and not jwt_secret:
            raise WechatConfigError("JWT_SECRET is required when APP_ENV=production")
        if auth_enabled and jwt_secret and hmac.compare_digest(identity_pepper, jwt_secret):
            raise WechatConfigError("WECHAT_IDENTITY_PEPPER must differ from the JWT signing secret")

        if provider == "real":
            if not app_secret:
                raise WechatConfigError("WECHAT_APP_SECRET is required when WECHAT_PROVIDER=real")
            if not identity_pepper:
                raise WechatConfigError("WECHAT_IDENTITY_PEPPER is required when WECHAT_PROVIDER=real")
        if (auth_enabled or provider == "real") and len(identity_pepper) < 32:
            raise WechatConfigError("WECHAT_IDENTITY_PEPPER must be at least 32 characters")

        try:
            api_timeout = int(os.getenv("WECHAT_API_TIMEOUT_SECONDS", "5"))
        except ValueError:
            raise WechatConfigError("WECHAT_API_TIMEOUT_SECONDS must be an integer")
        if api_timeout < 1 or api_timeout > 30:
            raise WechatConfigError("WECHAT_API_TIMEOUT_SECONDS must be between 1 and 30")

        try:
            challenge_minutes = int(os.getenv("WECHAT_BINDING_CHALLENGE_MINUTES", "10"))
        except ValueError:
            raise WechatConfigError("WECHAT_BINDING_CHALLENGE_MINUTES must be an integer")
        if challenge_minutes < 1 or challenge_minutes > 60:
            raise WechatConfigError("WECHAT_BINDING_CHALLENGE_MINUTES must be between 1 and 60")

        try:
            max_attempts = int(os.getenv("WECHAT_BINDING_MAX_ATTEMPTS", "5"))
        except ValueError:
            raise WechatConfigError("WECHAT_BINDING_MAX_ATTEMPTS must be an integer")
        if max_attempts < 1 or max_attempts > 20:
            raise WechatConfigError("WECHAT_BINDING_MAX_ATTEMPTS must be between 1 and 20")

        try:
            source_max_attempts = int(os.getenv("WECHAT_BINDING_SOURCE_MAX_ATTEMPTS", "20"))
            source_window_seconds = int(os.getenv("WECHAT_BINDING_SOURCE_WINDOW_SECONDS", "600"))
        except ValueError:
            raise WechatConfigError("WeChat source rate-limit values must be integers")
        if source_max_attempts < 1 or source_window_seconds < 1:
            raise WechatConfigError("WeChat source rate-limit values must be positive")

        source_pepper = os.getenv("WECHAT_SOURCE_FINGERPRINT_PEPPER", identity_pepper)

        return cls(
            auth_enabled=auth_enabled,
            provider=provider,
            app_id=app_id,
            app_secret=app_secret,
            identity_pepper=identity_pepper,
            api_timeout_seconds=api_timeout,
            binding_challenge_minutes=challenge_minutes,
            binding_max_attempts=max_attempts,
            binding_source_max_attempts=source_max_attempts,
            binding_source_window_seconds=source_window_seconds,
            source_fingerprint_pepper=source_pepper or identity_pepper,
        )

    @classmethod
    def for_tests(
        cls,
        *,
        app_id: str = "wx-test-app",
        app_secret: str = "test-secret",
        identity_pepper: str | None = None,
        auth_enabled: bool = True,
        provider: Literal["fake", "real"] = "fake",
    ) -> WechatConfig:
        pepper = identity_pepper or "test-only-wechat-identity-pepper"
        return cls(
            auth_enabled=auth_enabled,
            provider=provider,
            app_id=app_id,
            app_secret=app_secret,
            identity_pepper=pepper,
            api_timeout_seconds=5,
            binding_challenge_minutes=10,
            binding_max_attempts=5,
            binding_source_max_attempts=20,
            binding_source_window_seconds=600,
            source_fingerprint_pepper=pepper,
        )


class WechatConfigError(ValueError):
    pass


@lru_cache
def get_wechat_config() -> WechatConfig:
    return WechatConfig.from_env()
