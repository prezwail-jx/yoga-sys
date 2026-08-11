from app.main import app


class TestWechatAuthOpenApiPaths:
    """3.8 — 验证 /auth/wechat/session 和 /auth/wechat/bind 路径存在"""

    def test_wechat_session_path_exists(self):
        schema = app.openapi()
        paths = schema.get("paths", {})
        assert "/auth/wechat/session" in paths, (
            "/auth/wechat/session 不在 OpenAPI schema 中"
        )
        assert "post" in paths["/auth/wechat/session"]

    def test_wechat_bind_path_exists(self):
        schema = app.openapi()
        paths = schema.get("paths", {})
        assert "/auth/wechat/bind" in paths, (
            "/auth/wechat/bind 不在 OpenAPI schema 中"
        )
        assert "post" in paths["/auth/wechat/bind"]


class TestWechatAuthOpenApiNoSecurityRequired:
    """两个微信认证端点应该是匿名 (无 Bearer security)"""

    def test_session_endpoint_is_anonymous(self):
        schema = app.openapi()
        operation = schema["paths"]["/auth/wechat/session"]["post"]
        assert operation.get("security") is None or operation.get("security") == []

    def test_bind_endpoint_is_anonymous(self):
        schema = app.openapi()
        operation = schema["paths"]["/auth/wechat/bind"]["post"]
        assert operation.get("security") is None or operation.get("security") == []
