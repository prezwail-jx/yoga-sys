from fastapi.testclient import TestClient

from app.main import app

def test_openapi_exposes_us1_and_us2_real_paths() -> None:
    schema = app.openapi()
    expected_paths = {
        "/auth/login": {"post"}, "/auth/me": {"get"},
        "/members": {"get", "post"}, "/members/{memberId}": {"get", "patch", "delete"},
        "/card-products": {"get", "post"}, "/card-products/{product_id}": {"get", "patch"},
        "/members/me/cards": {"get"}, "/members/{memberId}/cards": {"get"}, "/transactions": {"post"},
        "/member-cards/{memberCardId}/freeze": {"post"}, "/member-cards/{memberCardId}/unfreeze": {"post"},
        "/member-cards/{memberCardId}/adjust-times": {"post"},
        "/writeoff/events": {"post"}, "/members/{memberId}/timeline": {"get"},
        "/courses": {"get", "post"}, "/courses/{courseId}": {"get", "patch"},
        "/rooms": {"get", "post"}, "/rooms/{roomId}": {"get", "patch"},
        "/coaches": {"get", "post"}, "/coaches/{coachId}": {"get", "patch"},
        "/class-sessions": {"get", "post"}, "/class-sessions/{sessionId}": {"get", "patch"},
        "/class-sessions/copy-week": {"post"},
        "/class-sessions/{sessionId}/publish": {"post"},
        "/class-sessions/{sessionId}/pause": {"post"},
        "/class-sessions/{sessionId}/resume": {"post"},
        "/class-sessions/{sessionId}/cancel": {"post"},
        "/class-sessions/{sessionId}/complete": {"post"},
        "/class-sessions/{sessionId}/bookings": {"get", "post"},
        "/class-bookings/{bookingId}/cancel": {"post"},
        "/class-bookings/{bookingId}/check-in": {"post"},
        "/members/me/bookings": {"get"},
        "/members/{memberId}/account": {"post"},
        "/coaches/{coachId}/account": {"post"},
    }
    openapi_paths = schema.get("paths", {})
    for path, methods in expected_paths.items():
        assert path in openapi_paths, f"Missing path in OpenAPI: {path}"
        assert methods <= set(openapi_paths[path]), f"Missing methods for {path}"

def test_openapi_secured_paths_include_bearer_auth() -> None:
    schema = app.openapi()
    assert "HTTPBearer" in schema.get("components", {}).get("securitySchemes", {})
    for path in ("/members", "/card-products", "/transactions", "/member-cards/{memberCardId}/freeze", "/member-cards/{memberCardId}/unfreeze", "/member-cards/{memberCardId}/adjust-times", "/writeoff/events", "/members/{memberId}/timeline", "/courses", "/rooms", "/coaches", "/class-sessions", "/class-sessions/copy-week"):
        for operation in schema["paths"][path].values():
            assert operation.get("security") == [{"HTTPBearer": []}]

def test_phase5_contract_includes_absence_and_timeline_pagination() -> None:
    schema = app.openapi()
    event_schema = schema["components"]["schemas"]["CreateWriteOffEventRequest"]
    assert set(event_schema["properties"]["eventType"]["enum"]) == {"reserve_hold", "checkin_commit", "cancel_refund", "absence_commit"}
    parameters = schema["paths"]["/members/{memberId}/timeline"]["get"]["parameters"]
    assert {"category", "action", "dateFrom", "dateTo", "businessRef", "skip", "limit"} <= {item["name"] for item in parameters}


def test_specific_course_ids_are_uuid_arrays_in_card_product_contract() -> None:
    schemas = app.openapi()["components"]["schemas"]
    for name in ("CreateCardProductRequest", "UpdateCardProductRequest"):
        field = schemas[name]["properties"]["specificCourseIds"]
        array_schema = next(item for item in field["anyOf"] if item.get("type") == "array")
        assert array_schema["items"] == {"type": "string", "format": "uuid"}


def test_phase4_write_operations_require_idempotency_key() -> None:
    schema = app.openapi()
    for path in ("/transactions", "/member-cards/{memberCardId}/freeze", "/member-cards/{memberCardId}/unfreeze", "/member-cards/{memberCardId}/adjust-times", "/writeoff/events"):
        parameters = schema["paths"][path]["post"].get("parameters", [])
        key = next(parameter for parameter in parameters if parameter["name"] == "Idempotency-Key")
        assert key["required"] is True


def test_member_contract_includes_card_summaries_and_adjust_type() -> None:
    schemas = app.openapi()["components"]["schemas"]
    assert "cardSummaries" in schemas["MemberResponse"]["properties"]
    transaction_types = schemas["CardTransactionResponse"]["properties"]["txnType"]["enum"]
    assert "adjust" in transaction_types


def test_group_class_critical_operations_require_idempotency_key() -> None:
    schema = app.openapi()
    for path in (
        "/class-sessions/copy-week",
        "/class-sessions/{sessionId}/cancel",
        "/class-sessions/{sessionId}/complete",
        "/class-sessions/{sessionId}/bookings",
        "/class-bookings/{bookingId}/cancel",
        "/class-bookings/{bookingId}/check-in",
        "/members/{memberId}/account",
        "/coaches/{coachId}/account",
    ):
        parameters = schema["paths"][path]["post"].get("parameters", [])
        key = next(parameter for parameter in parameters if parameter["name"] == "Idempotency-Key")
        assert key["required"] is True

def test_healthz_endpoint_available() -> None:
    response = TestClient(app).get("/healthz")
    assert response.status_code == 200 and response.json() == {"status": "ok"}
