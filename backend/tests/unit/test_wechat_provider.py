import hashlib
import hmac
import secrets
from unittest.mock import MagicMock, patch

import pytest

from app.core.wechat_config import WechatConfig
from app.integrations.wechat import (
    FakeWechatProvider,
    RealWechatProvider,
    WechatCodeInvalidError,
    WechatProviderBusyError,
    WechatProviderConfigError,
    WechatProviderInvalidResponseError,
    WechatProviderRateLimitedError,
    WechatProviderTimeoutError,
    WechatProviderUnavailableError,
    generate_binding_challenge,
    wechat_identity_digest,
    wechat_source_fingerprint,
    wechat_ticket_digest,
)


class TestFakeWechatProvider:
    def test_returns_deterministic_openid_for_same_code(self):
        config = WechatConfig.for_tests(app_id="wx-test")
        provider = FakeWechatProvider(config.app_id)
        session1 = provider.exchange("code-123")
        session2 = provider.exchange("code-123")
        assert session1.openid == session2.openid

    def test_different_codes_produce_different_openids(self):
        config = WechatConfig.for_tests(app_id="wx-test")
        provider = FakeWechatProvider(config.app_id)
        s1 = provider.exchange("code-1")
        s2 = provider.exchange("code-2")
        assert s1.openid != s2.openid

    def test_fake_identity_prefix_allows_a_new_code_for_the_same_user(self):
        provider = FakeWechatProvider("wx-test")
        first = provider.exchange("fake:member-1:nonce-a")
        repeat = provider.exchange("fake:member-1:nonce-b")
        assert first.openid == repeat.openid

    def test_different_appids_produce_different_openids(self):
        provider_a = FakeWechatProvider("app-a")
        provider_b = FakeWechatProvider("app-b")
        s_a = provider_a.exchange("code-1")
        s_b = provider_b.exchange("code-1")
        assert s_a.openid != s_b.openid

    def test_session_key_is_not_empty_and_unique(self):
        provider = FakeWechatProvider("wx-test")
        keys = {provider.exchange(f"code-{i}").session_key for i in range(5)}
        assert all(len(k) > 0 for k in keys)
        assert len(keys) == 5

    def test_unionid_is_none_by_default(self):
        provider = FakeWechatProvider("wx-test")
        session = provider.exchange("code-1")
        assert session.unionid is None


class TestDigestFunctions:
    @pytest.fixture
    def config(self):
        return WechatConfig.for_tests(
            app_id="wx-digest",
            identity_pepper="a" * 32,
        )

    def test_identity_digest_is_64_chars(self, config):
        digest = wechat_identity_digest(config, config.app_id, "oTest_openid")
        assert len(digest) == 64

    def test_identity_digest_includes_appid(self, config):
        d1 = wechat_identity_digest(config, "app-a", "openid-1")
        d2 = wechat_identity_digest(config, "app-b", "openid-1")
        assert d1 != d2

    def test_identity_digest_different_per_openid(self, config):
        d1 = wechat_identity_digest(config, config.app_id, "openid-a")
        d2 = wechat_identity_digest(config, config.app_id, "openid-b")
        assert d1 != d2

    def test_identity_digest_deterministic(self, config):
        d1 = wechat_identity_digest(config, config.app_id, "openid-1")
        d2 = wechat_identity_digest(config, config.app_id, "openid-1")
        assert d1 == d2

    def test_ticket_digest_is_64_chars(self, config):
        ticket = secrets.token_hex(32)
        digest = wechat_ticket_digest(config, ticket)
        assert len(digest) == 64

    def test_ticket_digest_deterministic(self, config):
        ticket = "fixed-ticket"
        d1 = wechat_ticket_digest(config, ticket)
        d2 = wechat_ticket_digest(config, ticket)
        assert d1 == d2

    def test_source_fingerprint_is_64_chars(self, config):
        fp = wechat_source_fingerprint(config, "1.2.3.4", "WeChat/7.0")
        assert len(fp) == 64

    def test_source_fingerprint_includes_both_ip_and_ua(self, config):
        fp1 = wechat_source_fingerprint(config, "1.2.3.4", "UA-A")
        fp2 = wechat_source_fingerprint(config, "1.2.3.4", "UA-B")
        fp3 = wechat_source_fingerprint(config, "5.6.7.8", "UA-A")
        assert fp1 != fp2
        assert fp1 != fp3


class TestGenerateBindingChallenge:
    @pytest.fixture
    def config(self):
        return WechatConfig.for_tests(
            app_id="wx-challenge",
            identity_pepper="b" * 32,
        )

    def test_returns_all_required_parts(self, config):
        result = generate_binding_challenge(config, config.app_id, "openid-1", "1.2.3.4", "UA")
        raw_ticket, ticket_digest, openid_digest, source_fp, expires_at = result
        assert len(raw_ticket) == 64
        assert len(ticket_digest) == 64
        assert len(openid_digest) == 64
        assert len(source_fp) == 64
        assert expires_at is not None

    def test_raw_ticket_differs_each_call(self, config):
        tickets = {
            generate_binding_challenge(config, config.app_id, "openid-1", "1.2.3.4", "UA")[0]
            for _ in range(5)
        }
        assert len(tickets) == 5

    def test_ticket_digest_matches_round_trip(self, config):
        raw, ticket_digest, *_ = generate_binding_challenge(
            config, config.app_id, "openid-1", "1.2.3.4", "UA"
        )
        expected_digest = hmac.new(
            config.identity_pepper.encode(), raw.encode(), hashlib.sha256
        ).hexdigest()
        assert ticket_digest == expected_digest

    def test_openid_digest_matches_identity_digest(self, config):
        _, _, openid_digest, _, _ = generate_binding_challenge(
            config, config.app_id, "openid-1", "1.2.3.4", "UA"
        )
        expected = wechat_identity_digest(config, config.app_id, "openid-1")
        assert openid_digest == expected


class TestRealWechatProvider:
    @pytest.fixture
    def config(self):
        return WechatConfig.for_tests(
            app_id="wx-test",
            app_secret="test-secret",
            identity_pepper="a" * 32,
        )

    def test_successful_exchange(self, config):
        response_data = {"openid": "oTest123", "session_key": "sk-abc"}
        mock_response = MagicMock()
        mock_response.json.return_value = response_data

        with patch("httpx.get", return_value=mock_response) as mock_get:
            provider = RealWechatProvider(config)
            session = provider.exchange("valid-code")

        assert session.openid == "oTest123"
        assert session.session_key == "sk-abc"
        assert session.unionid is None
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args.kwargs["params"]["appid"] == "wx-test"
        assert call_args.kwargs["params"]["secret"] == "test-secret"
        assert call_args.kwargs["params"]["js_code"] == "valid-code"
        assert call_args.kwargs["params"]["grant_type"] == "authorization_code"

    def test_success_with_unionid(self, config):
        response_data = {"openid": "oTest", "session_key": "sk", "unionid": "u-union"}
        mock_response = MagicMock()
        mock_response.json.return_value = response_data

        with patch("httpx.get", return_value=mock_response):
            session = RealWechatProvider(config).exchange("code")
        assert session.unionid == "u-union"

    def test_success_with_errcode_zero(self, config):
        response_data = {"errcode": 0, "openid": "oTest", "session_key": "sk"}
        mock_response = MagicMock()
        mock_response.json.return_value = response_data

        with patch("httpx.get", return_value=mock_response):
            session = RealWechatProvider(config).exchange("code")
        assert session.openid == "oTest"

    def test_code_invalid_40029(self, config):
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 40029, "errmsg": "invalid code"}

        with patch("httpx.get", return_value=mock_response):
            with pytest.raises(WechatCodeInvalidError):
                RealWechatProvider(config).exchange("bad-code")

    def test_rate_limited_45011(self, config):
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 45011, "errmsg": "rate limited"}

        with patch("httpx.get", return_value=mock_response):
            with pytest.raises(WechatProviderRateLimitedError):
                RealWechatProvider(config).exchange("code")

    def test_appsecret_error_40125(self, config):
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 40125, "errmsg": "secret error"}

        with patch("httpx.get", return_value=mock_response):
            with pytest.raises(WechatProviderConfigError):
                RealWechatProvider(config).exchange("code")

    def test_system_busy_neg1(self, config):
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": -1, "errmsg": "system busy"}

        with patch("httpx.get", return_value=mock_response):
            with pytest.raises(WechatProviderBusyError):
                RealWechatProvider(config).exchange("code")

    def test_missing_openid_raises(self, config):
        mock_response = MagicMock()
        mock_response.json.return_value = {"session_key": "sk"}

        with patch("httpx.get", return_value=mock_response):
            with pytest.raises(WechatProviderInvalidResponseError):
                RealWechatProvider(config).exchange("code")

    def test_missing_session_key_raises(self, config):
        mock_response = MagicMock()
        mock_response.json.return_value = {"openid": "oTest"}

        with patch("httpx.get", return_value=mock_response):
            with pytest.raises(WechatProviderInvalidResponseError):
                RealWechatProvider(config).exchange("code")

    def test_non_json_response_raises(self, config):
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("not json")

        with patch("httpx.get", return_value=mock_response):
            with pytest.raises(WechatProviderInvalidResponseError):
                RealWechatProvider(config).exchange("code")

    def test_timeout_raises(self, config):
        import httpx

        with patch("httpx.get", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(WechatProviderTimeoutError):
                RealWechatProvider(config).exchange("code")

    def test_request_error_raises(self, config):
        import httpx

        with patch("httpx.get", side_effect=httpx.RequestError("conn err")):
            with pytest.raises(WechatProviderUnavailableError):
                RealWechatProvider(config).exchange("code")
