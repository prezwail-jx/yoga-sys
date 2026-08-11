import os
from unittest.mock import patch

import pytest

from app.core.wechat_config import WechatConfig, WechatConfigError


class TestWechatConfigValidation:
    def test_defaults_to_fake_disabled(self):
        env = {"WECHAT_APP_ID": "wx-test"}
        with patch.dict(os.environ, env, clear=True):
            config = WechatConfig.from_env()
        assert config.provider == "fake"
        assert config.auth_enabled is False

    def test_explicit_values_are_respected(self):
        env = {
            "WECHAT_AUTH_ENABLED": "true",
            "WECHAT_PROVIDER": "fake",
            "WECHAT_APP_ID": "wx-test",
            "WECHAT_IDENTITY_PEPPER": "a" * 32,
            "WECHAT_API_TIMEOUT_SECONDS": "7",
            "WECHAT_BINDING_CHALLENGE_MINUTES": "15",
            "WECHAT_BINDING_MAX_ATTEMPTS": "3",
        }
        with patch.dict(os.environ, env, clear=True):
            config = WechatConfig.from_env()
        assert config.auth_enabled is True
        assert config.provider == "fake"
        assert config.app_id == "wx-test"
        assert config.api_timeout_seconds == 7
        assert config.binding_challenge_minutes == 15
        assert config.binding_max_attempts == 3

    def test_rejects_production_fake_provider(self):
        env = {"APP_ENV": "production", "WECHAT_PROVIDER": "fake", "WECHAT_APP_ID": "wx-test"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(WechatConfigError, match="production"):
                WechatConfig.from_env()

    def test_rejects_real_without_secret(self):
        env = {"WECHAT_PROVIDER": "real", "WECHAT_APP_ID": "wx-test", "WECHAT_APP_SECRET": ""}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(WechatConfigError, match="WECHAT_APP_SECRET"):
                WechatConfig.from_env()

    def test_rejects_real_without_pepper(self):
        env = {
            "WECHAT_PROVIDER": "real",
            "WECHAT_APP_ID": "wx-test",
            "WECHAT_APP_SECRET": "s",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(WechatConfigError, match="WECHAT_IDENTITY_PEPPER"):
                WechatConfig.from_env()

    def test_rejects_real_with_short_pepper(self):
        env = {
            "WECHAT_PROVIDER": "real",
            "WECHAT_APP_ID": "wx-test",
            "WECHAT_APP_SECRET": "s",
            "WECHAT_IDENTITY_PEPPER": "short",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(WechatConfigError, match="32"):
                WechatConfig.from_env()

    def test_rejects_identity_pepper_reused_as_jwt_secret(self):
        env = {
            "WECHAT_AUTH_ENABLED": "true",
            "WECHAT_APP_ID": "wx-test",
            "WECHAT_IDENTITY_PEPPER": "a" * 32,
            "JWT_SECRET": "a" * 32,
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(WechatConfigError, match="must differ"):
                WechatConfig.from_env()

    def test_rejects_short_pepper_for_enabled_fake_provider(self):
        env = {
            "WECHAT_AUTH_ENABLED": "true",
            "WECHAT_APP_ID": "wx-test",
            "WECHAT_IDENTITY_PEPPER": "short",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(WechatConfigError, match="at least 32"):
                WechatConfig.from_env()

    def test_rejects_missing_production_jwt_secret(self):
        env = {
            "APP_ENV": "production",
            "WECHAT_PROVIDER": "real",
            "WECHAT_APP_ID": "wx-test",
            "WECHAT_APP_SECRET": "secret",
            "WECHAT_IDENTITY_PEPPER": "a" * 32,
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(WechatConfigError, match="JWT_SECRET"):
                WechatConfig.from_env()

    def test_rejects_invalid_provider_value(self):
        env = {"WECHAT_PROVIDER": "invalid_provider", "WECHAT_APP_ID": "wx-test"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(WechatConfigError, match="invalid_provider"):
                WechatConfig.from_env()

    def test_rejects_invalid_timeout(self):
        env = {
            "WECHAT_APP_ID": "wx-test",
            "WECHAT_API_TIMEOUT_SECONDS": "0",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(WechatConfigError, match="between 1 and 30"):
                WechatConfig.from_env()

    def test_rejects_invalid_challenge_minutes(self):
        env = {
            "WECHAT_APP_ID": "wx-test",
            "WECHAT_BINDING_CHALLENGE_MINUTES": "61",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(WechatConfigError, match="between 1 and 60"):
                WechatConfig.from_env()

    def test_rejects_invalid_max_attempts(self):
        env = {
            "WECHAT_APP_ID": "wx-test",
            "WECHAT_BINDING_MAX_ATTEMPTS": "0",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(WechatConfigError, match="between 1 and 20"):
                WechatConfig.from_env()

    def test_missing_app_id_is_rejected(self):
        env = {"WECHAT_AUTH_ENABLED": "true", "WECHAT_APP_ID": "", "WECHAT_IDENTITY_PEPPER": "a" * 32}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(WechatConfigError, match="WECHAT_APP_ID"):
                WechatConfig.from_env()

    def test_for_tests_convenience(self):
        config = WechatConfig.for_tests(app_id="wx-test", identity_pepper="a" * 32)
        assert config.app_id == "wx-test"
        assert config.provider == "fake"
        assert config.auth_enabled is True
        assert config.api_timeout_seconds == 5
        assert config.binding_challenge_minutes == 10
        assert config.binding_max_attempts == 5

    def test_error_message_does_not_contain_secrets(self):
        env = {"WECHAT_AUTH_ENABLED": "true", "WECHAT_APP_ID": "", "WECHAT_IDENTITY_PEPPER": "a" * 32}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(WechatConfigError) as exc_info:
                WechatConfig.from_env()
        assert "APP_SECRET" not in str(exc_info.value)
