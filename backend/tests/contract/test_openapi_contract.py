from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app


def test_openapi_exposes_required_paths() -> None:
    schema = app.openapi()
    expected_paths = {
        "/members": {"post"},
        "/members/{memberId}": {"patch", "delete"},
        "/members/{memberId}/timeline": {"get"},
        "/card-products": {"post"},
        "/member-cards/{memberCardId}/freeze": {"post"},
        "/member-cards/{memberCardId}/unfreeze": {"post"},
        "/transactions": {"post"},
        "/writeoff/events": {"post"},
    }

    openapi_paths = schema.get("paths", {})
    for path, methods in expected_paths.items():
        assert path in openapi_paths, f"Missing path in OpenAPI: {path}"
        for method in methods:
            assert method in openapi_paths[path], f"Missing method {method} in {path}"


def test_openapi_secured_paths_include_bearer_auth() -> None:
    schema = app.openapi()
    security_schemes = schema.get("components", {}).get("securitySchemes", {})
    # Security scheme will be emitted once protected endpoints are bound via Depends(HTTPBearer)
    assert "HTTPBearer" in security_schemes or "bearerAuth" in security_schemes


def test_healthz_endpoint_available() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
