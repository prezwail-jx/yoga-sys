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
        "/writeoff/events": {"post"}, "/members/{memberId}/timeline": {"get"},
    }
    openapi_paths = schema.get("paths", {})
    for path, methods in expected_paths.items():
        assert path in openapi_paths, f"Missing path in OpenAPI: {path}"
        assert methods <= set(openapi_paths[path]), f"Missing methods for {path}"

def test_openapi_secured_paths_include_bearer_auth() -> None:
    schema = app.openapi()
    assert "HTTPBearer" in schema.get("components", {}).get("securitySchemes", {})
    for path in ("/members", "/card-products", "/transactions", "/member-cards/{memberCardId}/freeze", "/member-cards/{memberCardId}/unfreeze", "/writeoff/events", "/members/{memberId}/timeline"):
        for operation in schema["paths"][path].values():
            assert operation.get("security") == [{"HTTPBearer": []}]

def test_phase5_contract_includes_absence_and_timeline_pagination() -> None:
    schema = app.openapi()
    event_schema = schema["components"]["schemas"]["CreateWriteOffEventRequest"]
    assert set(event_schema["properties"]["eventType"]["enum"]) == {"reserve_hold", "checkin_commit", "cancel_refund", "absence_commit"}
    parameters = schema["paths"]["/members/{memberId}/timeline"]["get"]["parameters"]
    assert {"category", "action", "dateFrom", "dateTo", "businessRef", "skip", "limit"} <= {item["name"] for item in parameters}


def test_phase4_write_operations_require_idempotency_key() -> None:
    schema = app.openapi()
    for path in ("/transactions", "/member-cards/{memberCardId}/freeze", "/member-cards/{memberCardId}/unfreeze", "/writeoff/events"):
        parameters = schema["paths"][path]["post"].get("parameters", [])
        key = next(parameter for parameter in parameters if parameter["name"] == "Idempotency-Key")
        assert key["required"] is True

def test_healthz_endpoint_available() -> None:
    response = TestClient(app).get("/healthz")
    assert response.status_code == 200 and response.json() == {"status": "ok"}
