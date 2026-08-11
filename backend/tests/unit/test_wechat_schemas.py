import pytest

from app.schemas.wechat_auth import (
    WechatBindRequest,
    WechatBindResponse,
    WechatSessionRequest,
    WechatSessionResponse,
)


class TestWechatSessionRequest:
    def test_valid_code(self):
        req = WechatSessionRequest(code="081abc123")
        assert req.code == "081abc123"

    def test_empty_code_rejected(self):
        with pytest.raises(ValueError):
            WechatSessionRequest(code="")

    @pytest.mark.parametrize("code_len", [512, 511])
    def test_max_length_accepted(self, code_len):
        req = WechatSessionRequest(code="a" * code_len)
        assert len(req.code) == code_len

    def test_too_long_code_rejected(self):
        with pytest.raises(ValueError):
            WechatSessionRequest(code="a" * 513)


class TestWechatSessionResponse:
    def test_bound_response(self):
        resp = WechatSessionResponse(
            state="bound",
            access_token="eyJ...",
            token_type="bearer",
            role="member",
        )
        assert resp.state == "bound"
        assert resp.binding_ticket is None
        assert resp.error is None

    def test_binding_required_response(self):
        resp = WechatSessionResponse(
            state="binding_required",
            binding_ticket="ticket-abc",
            expires_in=600,
        )
        assert resp.state == "binding_required"
        assert resp.access_token is None
        assert resp.error is None

    def test_error_response(self):
        resp = WechatSessionResponse(
            state="error",
            error="wechat_code_invalid",
            error_description="Code expired",
        )
        assert resp.state == "error"
        assert resp.access_token is None

    def test_camel_case_serialization(self):
        resp = WechatSessionResponse(
            state="bound",
            access_token="eyJ...",
            token_type="bearer",
            role="member",
        )
        data = resp.model_dump(by_alias=True)
        assert "accessToken" in data
        assert "tokenType" in data
        assert "access_token" not in data


class TestWechatBindRequest:
    def test_valid_request(self):
        req = WechatBindRequest(
            binding_ticket="ticket-123",
            username=" member-user ",
            password="secret123",
        )
        assert req.binding_ticket == "ticket-123"
        assert req.username == "member-user"

    def test_empty_fields_rejected(self):
        with pytest.raises(ValueError):
            WechatBindRequest(binding_ticket="", username="user", password="pass")

    @pytest.mark.parametrize("field", ["binding_ticket", "username", "password"])
    def test_min_length_enforced(self, field):
        kwargs = {"binding_ticket": "ticket", "username": "user", "password": "pass"}
        kwargs[field] = ""
        with pytest.raises(ValueError):
            WechatBindRequest(**kwargs)


class TestWechatBindResponse:
    def test_bind_response(self):
        resp = WechatBindResponse(
            access_token="eyJ...",
            role="member",
        )
        assert resp.access_token == "eyJ..."
        assert resp.role == "member"
        assert resp.token_type == "bearer"

    def test_camel_case_serialization(self):
        resp = WechatBindResponse(access_token="eyJ...", role="coach")
        data = resp.model_dump(by_alias=True)
        assert "accessToken" in data
        assert "tokenType" in data
