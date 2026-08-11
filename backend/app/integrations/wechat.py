from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from app.core.wechat_config import WechatConfig


@dataclass(frozen=True)
class WechatSession:
    openid: str
    session_key: str
    unionid: str | None = None


class WechatCodeExchangeProvider(Protocol):
    def exchange(self, code: str) -> WechatSession: ...


class FakeWechatProvider:
    def __init__(self, app_id: str) -> None:
        self._app_id = app_id

    def exchange(self, code: str) -> WechatSession:
        openid = _derive_openid(self._app_id, code)
        session_key = secrets.token_hex(32)
        return WechatSession(openid=openid, session_key=session_key)


class RealWechatProvider:
    def __init__(self, config: WechatConfig) -> None:
        self._app_id = config.app_id
        self._app_secret = config.app_secret
        self._timeout = config.api_timeout_seconds

    def exchange(self, code: str) -> WechatSession:
        import httpx

        try:
            response = httpx.get(
                "https://api.weixin.qq.com/sns/jscode2session",
                params={
                    "appid": self._app_id,
                    "secret": self._app_secret,
                    "js_code": code,
                    "grant_type": "authorization_code",
                },
                timeout=self._timeout,
            )
        except httpx.TimeoutException:
            raise WechatProviderTimeoutError("WeChat code2Session timed out")
        except httpx.RequestError as exc:
            raise WechatProviderUnavailableError("WeChat API unreachable") from exc

        try:
            data = response.json()
        except ValueError:
            raise WechatProviderInvalidResponseError("WeChat returned non-JSON response")

        errcode = data.get("errcode")
        if errcode is not None and errcode != 0:
            if errcode == 40029:
                raise WechatCodeInvalidError("WeChat code invalid or expired")
            if errcode == 45011:
                raise WechatProviderRateLimitedError("WeChat rate limited")
            if errcode == 40125:
                raise WechatProviderConfigError("WeChat AppSecret is invalid or reset")
            if errcode == 40226:
                raise WechatLoginRejectedError("WeChat login blocked for high-risk user")
            if errcode == -1:
                raise WechatProviderBusyError("WeChat system busy")
            raise WechatProviderError(f"WeChat error {errcode}")

        openid = data.get("openid")
        session_key = data.get("session_key")
        if not openid or not session_key:
            raise WechatProviderInvalidResponseError("WeChat response missing openid or session_key")

        return WechatSession(
            openid=openid,
            session_key=session_key,
            unionid=data.get("unionid"),
        )


def wechat_identity_digest(config: WechatConfig, appid: str, openid: str) -> str:
    pepper = config.identity_pepper.encode()
    message = f"{appid}:{openid}".encode()
    return hmac.new(pepper, message, hashlib.sha256).hexdigest()


def wechat_ticket_digest(config: WechatConfig, ticket: str) -> str:
    return hmac.new(
        config.identity_pepper.encode(), ticket.encode(), hashlib.sha256
    ).hexdigest()


def wechat_source_fingerprint(config: WechatConfig, client_ip: str, user_agent: str) -> str:
    pepper = config.source_fingerprint_pepper.encode()
    message = f"{client_ip}\0{user_agent}".encode()
    return hmac.new(pepper, message, hashlib.sha256).hexdigest()


def generate_binding_challenge(
    config: WechatConfig,
    appid: str,
    openid: str,
    client_ip: str,
    user_agent: str,
    *,
    now: datetime | None = None,
) -> tuple[str, str, str, str, datetime]:
    raw_ticket = secrets.token_hex(32)
    ticket_digest = wechat_ticket_digest(config, raw_ticket)
    openid_digest = wechat_identity_digest(config, appid, openid)
    source_fingerprint = wechat_source_fingerprint(config, client_ip, user_agent)
    expires_at = (now or datetime.now(timezone.utc)) + timedelta(
        minutes=config.binding_challenge_minutes
    )
    return raw_ticket, ticket_digest, openid_digest, source_fingerprint, expires_at


def _derive_openid(app_id: str, code: str) -> str:
    # fake:<identity>:<nonce> models repeated wx.login calls for one test user.
    identity = code.split(":", 2)[1] if code.startswith("fake:") and code.count(":") >= 2 else code
    key = f"{app_id}:{identity}".encode()
    digest = hashlib.sha256(key).hexdigest()
    return f"o{app_id[2:]}_{digest[:16]}"


class WechatProviderError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class WechatCodeInvalidError(WechatProviderError):
    pass


class WechatProviderTimeoutError(WechatProviderError):
    pass


class WechatProviderUnavailableError(WechatProviderError):
    pass


class WechatProviderInvalidResponseError(WechatProviderError):
    pass


class WechatProviderRateLimitedError(WechatProviderError):
    pass


class WechatProviderConfigError(WechatProviderError):
    pass


class WechatLoginRejectedError(WechatProviderError):
    pass


class WechatProviderBusyError(WechatProviderError):
    pass
