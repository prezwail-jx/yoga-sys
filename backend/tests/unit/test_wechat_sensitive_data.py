import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.middleware.request_context import RequestContextMiddleware
from app.infra.observability import redact_sensitive_fields

# ----------------------------------------------------------------
# 脱敏扫描工具 — 检查字符串 / dict / 列表中是否意外出现敏感值
# ----------------------------------------------------------------

_SENSITIVE_PATTERNS: list[tuple[str, str]] = [
    ("JWT (eyJ...)", r"eyJ[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+"),
    ("raw ticket (64 hex)", r"\b[a-f0-9]{64}\b"),
    ("session_key", r"session_key"),
    ("openid (o开头)", r'"\s*o[A-Za-z0-9\-_]{27}\s*"'),
    ("password 字段值", r'"password"\s*:\s*"(?!\*\*\*)[^"]+'),
    ("AppSecret 裸值", r"55d494ee"),
]

_SENSITIVE_FIELD_NAMES = {
    "password",
    "app_secret",
    "appsecret",
    "session_key",
    "sessionKey",
    "identity_pepper",
    "pepper",
}


def _find_sensitive_fields(
    data: Any, path: str = "", max_depth: int = 8
) -> list[str]:
    if max_depth <= 0:
        return []
    findings: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key.lower() in _SENSITIVE_FIELD_NAMES and value not in (None, "", "***REDACTED***"):
                findings.append(f"{path}.{key} = {_truncate(value)!r}")
            findings.extend(_find_sensitive_fields(value, f"{path}.{key}", max_depth - 1))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            findings.extend(_find_sensitive_fields(item, f"{path}[{idx}]", max_depth - 1))
    return findings


def _scan_text(text: str) -> list[str]:
    findings: list[str] = []
    for name, pattern in _SENSITIVE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            findings.append(name)
    return findings


def _truncate(value: Any) -> str:
    s = str(value)
    return s[:40] + "..." if len(s) > 40 else s


# ----------------------------------------------------------------
# 扫描测试: 错误响应不应含有敏感值
# ----------------------------------------------------------------

class TestNoSensitiveDataInErrorResponses:
    def test_error_code_messages_are_safe(self):
        from app.schemas.wechat_auth import WechatErrorCode

        codes = [
            getattr(WechatErrorCode, attr)
            for attr in dir(WechatErrorCode)
            if not attr.startswith("_") and attr.isupper()
        ]
        for code in codes:
            assert isinstance(code, str)
            findings = _scan_text(code)
            assert not findings, f"错误码 '{code}' 触发了脱敏规则: {findings}"

    @pytest.mark.parametrize(
        "error_response",
        [
            {"state": "error", "error": "wechat_code_invalid", "errorDescription": "Code expired"},
            {"state": "error", "error": "wechat_provider_unavailable", "errorDescription": "Upstream unreachable"},
            {"state": "error", "error": "account_disabled", "errorDescription": "Account is disabled"},
            {"state": "error", "error": "binding_credentials_rejected"},
        ],
    )
    def test_session_error_responses_contain_no_secrets(self, error_response):
        from app.schemas.wechat_auth import WechatSessionResponse

        resp = WechatSessionResponse(**error_response)
        json_str = resp.model_dump_json()
        findings = _scan_text(json_str)
        assert not findings, f"Session 错误响应包含敏感值: {findings}"

    @pytest.mark.parametrize(
        "bind_response",
        [
            {"accessToken": "eyJ..." * 5, "tokenType": "bearer", "role": "member"},
        ],
    )
    def test_bind_responses_contain_no_password(self, bind_response):
        from app.schemas.wechat_auth import WechatBindResponse

        resp = WechatBindResponse(**bind_response)
        json_str = resp.model_dump_json(by_alias=True)
        findings = _scan_text(json_str)
        allowed = {"JWT (eyJ...)"}
        unexpected = {f for f in findings if f not in allowed}
        assert not unexpected, f"Bind 响应包含意外敏感值: {unexpected}"

    def test_config_error_does_not_expose_secrets(self):
        from app.core.wechat_config import WechatConfigError

        msg = "WECHAT_APP_SECRET is required when WECHAT_PROVIDER=real"
        exc = WechatConfigError(msg)
        assert "55d" not in str(exc)
        findings = _scan_text(str(exc))
        assert not findings, f"配置错误消息含敏感值: {findings}"


class TestProviderErrorMessagesAreSafe:
    def test_all_provider_error_classes_have_safe_messages(self):
        from app.integrations.wechat import (
            WechatCodeInvalidError,
            WechatLoginRejectedError,
            WechatProviderBusyError,
            WechatProviderConfigError,
            WechatProviderInvalidResponseError,
            WechatProviderRateLimitedError,
            WechatProviderTimeoutError,
            WechatProviderUnavailableError,
        )

        errors = [
            WechatCodeInvalidError("invalid"),
            WechatProviderRateLimitedError("rate"),
            WechatProviderConfigError("config"),
            WechatLoginRejectedError("rejected"),
            WechatProviderBusyError("busy"),
            WechatProviderTimeoutError("timeout"),
            WechatProviderUnavailableError("unavailable"),
            WechatProviderInvalidResponseError("bad response"),
        ]
        for exc in errors:
            findings = _scan_text(str(exc))
            assert not findings, f"{type(exc).__name__} 消息含敏感值: {findings}"


class TestDigestsAreNotReversible:
    def test_identity_digest_does_not_contain_raw_openid(self):
        from app.core.wechat_config import WechatConfig
        from app.integrations.wechat import wechat_identity_digest

        config = WechatConfig.for_tests(app_id="wx-test", identity_pepper="c" * 32)
        raw_openid = "oABC1234567890123456789012345"
        digest = wechat_identity_digest(config, config.app_id, raw_openid)
        assert raw_openid not in digest
        assert "openid" not in digest.lower()
        assert hashlib.sha256(raw_openid.encode()).hexdigest() != digest

    def test_ticket_digest_does_not_contain_raw_ticket(self):
        from app.core.wechat_config import WechatConfig
        from app.integrations.wechat import wechat_ticket_digest

        config = WechatConfig.for_tests(app_id="wx-test", identity_pepper="d" * 32)
        raw_ticket = "a" * 64
        digest = wechat_ticket_digest(config, raw_ticket)
        assert raw_ticket not in digest
        assert hashlib.sha256(raw_ticket.encode()).hexdigest() != digest


class _RecordingSpan:
    def __init__(self) -> None:
        self.attributes: dict[str, Any] = {}

    def get_span_context(self):
        return SimpleNamespace(span_id=1)

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def set_status(self, _status: Any) -> None:
        return None

    def record_exception(self, _exc: Exception) -> None:
        return None


class _SpanContext:
    def __init__(self, span: _RecordingSpan) -> None:
        self.span = span

    def __enter__(self) -> _RecordingSpan:
        return self.span

    def __exit__(self, *_args: Any) -> None:
        return None


class _RecordingTracer:
    def __init__(self) -> None:
        self.span = _RecordingSpan()

    def start_as_current_span(self, _name: str) -> _SpanContext:
        return _SpanContext(self.span)


class _RecordingLogger:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def info(self, event: str, **values: Any) -> None:
        self.events.append({"event": event, **values})


class TestObservabilityBoundaries:
    def test_structured_log_processor_redacts_nested_sensitive_fields(self):
        event = {
            "event": "probe",
            "authorization": "Bearer secret-jwt",
            "request": {
                "password": "secret-password",
                "bindingTicket": "secret-ticket",
                "safe": "visible",
            },
            "items": [{"session_key": "secret-session"}],
        }

        redacted = redact_sensitive_fields(None, "info", event)

        serialized = json.dumps(redacted)
        assert "secret-jwt" not in serialized
        assert "secret-password" not in serialized
        assert "secret-ticket" not in serialized
        assert "secret-session" not in serialized
        assert redacted["request"]["safe"] == "visible"

    def test_request_middleware_does_not_trace_headers_query_or_body(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        tracer = _RecordingTracer()
        logger = _RecordingLogger()
        monkeypatch.setattr(
            "app.api.middleware.request_context.get_tracer", lambda: tracer
        )
        monkeypatch.setattr(
            "app.api.middleware.request_context.get_logger", lambda: logger
        )
        app = FastAPI()
        app.add_middleware(RequestContextMiddleware)

        @app.post("/probe")
        def probe():
            return {"state": "safe"}

        canaries = [
            "secret-app-value",
            "secret-password-value",
            "secret-jwt-value",
            "secret-ticket-value",
            "secret-openid-value",
            "secret-session-value",
        ]
        response = TestClient(app).post(
            "/probe?bindingTicket=secret-ticket-value",
            headers={
                "Authorization": "Bearer secret-jwt-value",
                "X-App-Secret": "secret-app-value",
                "X-Trace-Id": "safe-trace-id",
            },
            json={
                "password": "secret-password-value",
                "openid": "secret-openid-value",
                "session_key": "secret-session-value",
            },
        )

        assert response.json() == {"state": "safe"}
        observed = json.dumps(
            {"logs": logger.events, "spans": tracer.span.attributes}
        )
        assert all(canary not in observed for canary in canaries)
        assert tracer.span.attributes["url.path"] == "/probe"

    def test_production_source_contains_no_embedded_wechat_secret_or_jwt(self):
        backend_root = Path(__file__).resolve().parents[2] / "app"
        miniapp_root = Path(__file__).resolve().parents[3] / "miniapp" / "miniprogram"
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for root in (backend_root, miniapp_root)
            for pattern in ("*.py", "*.ts")
            for path in root.rglob(pattern)
        )
        forbidden = {
            "embedded AppSecret": r"WECHAT_APP_SECRET\s*=\s*['\"][^'\"]+",
            "embedded identity pepper": r"WECHAT_IDENTITY_PEPPER\s*=\s*['\"][^'\"]+",
            "embedded JWT": r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
        }

        findings = [name for name, pattern in forbidden.items() if re.search(pattern, source)]
        assert not findings, f"production source contains sensitive literals: {findings}"
