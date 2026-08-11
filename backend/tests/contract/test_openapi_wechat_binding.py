from app.main import app


class TestWechatBindingOpenApiPaths:
    """4.4 — 验证 /accounts/{accountId}/wechat-binding 路径存在"""

    def test_wechat_binding_path_exists(self):
        schema = app.openapi()
        paths = schema.get("paths", {})
        assert "/accounts/{accountId}/wechat-binding" in paths, (
            "/accounts/{accountId}/wechat-binding 不在 OpenAPI schema 中"
        )
        path_ops = paths["/accounts/{accountId}/wechat-binding"]
        assert "get" in path_ops
        assert "delete" in path_ops

    def test_wechat_binding_requires_admin(self):
        schema = app.openapi()
        path_ops = schema["paths"]["/accounts/{accountId}/wechat-binding"]
        for method in ("get", "delete"):
            op = path_ops[method]
            assert op.get("security") == [{"HTTPBearer": []}], (
                f"/accounts/{{accountId}}/wechat-binding {method} 缺少管理员 Bearer 安全要求"
            )

    def test_delete_wechat_binding_has_confirm_body(self):
        schema = app.openapi()
        delete_op = schema["paths"]["/accounts/{accountId}/wechat-binding"]["delete"]
        request_body = delete_op.get("requestBody")
        assert request_body is not None, "DELETE 操作缺少 requestBody"
        ref = request_body.get("content", {}).get("application/json", {}).get("schema", {}).get("$ref")
        assert ref is not None
        schema_name = ref.split("/")[-1]
        assert schema_name == "UnbindConfirmationRequest"
