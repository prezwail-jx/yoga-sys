from fastapi.testclient import TestClient

from app.main import app

def test_openapi_exposes_us1_and_us2_real_paths() -> None:
    schema = app.openapi()
    expected_paths = {
        "/auth/login": {"post"}, "/auth/me": {"get"},
        "/members": {"get", "post"}, "/members/{memberId}": {"get", "patch", "delete"},
        "/card-products": {"get", "post"}, "/card-products/{product_id}": {"get", "patch"},
        "/members/{memberId}/cards": {"get"}, "/transactions": {"post"},
        "/member-cards/{memberCardId}/freeze": {"post"}, "/member-cards/{memberCardId}/unfreeze": {"post"},
    }
    openapi_paths = schema.get("paths", {})
    for path, methods in expected_paths.items():
        assert path in openapi_paths, f"Missing path in OpenAPI: {path}"
        assert methods <= set(openapi_paths[path]), f"Missing methods for {path}"

def test_openapi_secured_paths_include_bearer_auth() -> None:
    schema = app.openapi()
    assert "HTTPBearer" in schema.get("components", {}).get("securitySchemes", {})
    for path in ("/members", "/card-products", "/transactions", "/member-cards/{memberCardId}/freeze", "/member-cards/{memberCardId}/unfreeze"):
        for operation in schema["paths"][path].values():
            assert operation.get("security") == [{"HTTPBearer": []}]

def test_phase4_write_operations_require_idempotency_key() -> None:
    schema = app.openapi()
    for path in ("/transactions", "/member-cards/{memberCardId}/freeze", "/member-cards/{memberCardId}/unfreeze"):
        parameters = schema["paths"][path]["post"].get("parameters", [])
        key = next(parameter for parameter in parameters if parameter["name"] == "Idempotency-Key")
        assert key["required"] is True

def test_healthz_endpoint_available() -> None:
    response = TestClient(app).get("/healthz")
    assert response.status_code == 200 and response.json() == {"status": "ok"}
