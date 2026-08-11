from pathlib import Path

import yaml
import schemathesis

from app.schemas.class_catalog import CreateCourseRequest, UpdateCourseRequest
from app.schemas.class_scheduling import CreateClassSessionRequest
from app.schemas.account_binding import AccountBindingResponse, CreateAccountBindingRequest


CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs/contracts/group-class-booking.openapi.yaml"
)


def load_contract() -> dict:
    return yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))


def operation(contract: dict, path: str, method: str) -> dict:
    return contract["paths"][path][method]


def test_contract_is_valid_openapi() -> None:
    schema = schemathesis.openapi.from_path(str(CONTRACT_PATH))
    assert len(schema.raw_schema["paths"]) == 20


def test_contract_exposes_group_class_paths() -> None:
    contract = load_contract()
    expected = {
        "/courses": {"get", "post"},
        "/courses/{courseId}": {"get", "patch"},
        "/rooms": {"get", "post"},
        "/rooms/{roomId}": {"get", "patch"},
        "/coaches": {"get", "post"},
        "/coaches/{coachId}": {"get", "patch"},
        "/class-sessions": {"get", "post"},
        "/class-sessions/{sessionId}": {"get", "patch"},
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
    for path, methods in expected.items():
        assert path in contract["paths"]
        assert methods <= set(contract["paths"][path])


def test_contract_secures_all_operations_with_bearer_auth() -> None:
    contract = load_contract()
    assert contract["security"] == [{"bearerAuth": []}]
    assert contract["components"]["securitySchemes"]["bearerAuth"]["scheme"] == "bearer"


def test_critical_writes_require_idempotency_key() -> None:
    contract = load_contract()
    critical_operations = (
        ("/class-sessions/copy-week", "post"),
        ("/class-sessions/{sessionId}/cancel", "post"),
        ("/class-sessions/{sessionId}/complete", "post"),
        ("/class-sessions/{sessionId}/bookings", "post"),
        ("/class-bookings/{bookingId}/cancel", "post"),
        ("/class-bookings/{bookingId}/check-in", "post"),
        ("/members/{memberId}/account", "post"),
        ("/coaches/{coachId}/account", "post"),
    )
    for path, method in critical_operations:
        references = {item.get("$ref") for item in operation(contract, path, method).get("parameters", [])}
        assert "#/components/parameters/IdempotencyKey" in references, path


def test_contract_enums_and_relative_booking_rules_match_models() -> None:
    schemas = load_contract()["components"]["schemas"]
    assert set(schemas["CourseDifficulty"]["enum"]) == {
        "all_levels", "beginner", "intermediate", "advanced",
    }
    assert set(schemas["ClassSessionStatus"]["enum"]) == {
        "draft", "published", "paused", "cancelled", "completed",
    }
    assert set(schemas["ClassBookingStatus"]["enum"]) == {
        "reserved", "checked_in", "cancelled", "absent",
    }
    properties = schemas["CreateClassSessionRequest"]["properties"]
    assert {
        "bookingOpenHoursBefore", "bookingCloseMinutesBefore", "cancelCutoffMinutesBefore",
    } <= set(properties)


def test_member_account_response_never_exposes_password_fields() -> None:
    schemas = load_contract()["components"]["schemas"]
    account_properties = set(schemas["AccountBinding"]["properties"])
    assert "initialPassword" not in account_properties
    assert "password" not in account_properties
    assert "passwordHash" not in account_properties
    assert schemas["CreateAccountBindingRequest"]["properties"]["initialPassword"]["writeOnly"] is True


def test_class_session_response_exposes_derived_capacity_fields() -> None:
    schemas = load_contract()["components"]["schemas"]
    derived = schemas["ClassSession"]["allOf"][1]["properties"]
    assert {"bookedCount", "remainingCapacity", "isFull"} <= set(derived)


def test_pydantic_schemas_use_contract_camel_case_fields() -> None:
    contract_schemas = load_contract()["components"]["schemas"]
    pairs = (
        (CreateCourseRequest, "CreateCourseRequest"),
        (UpdateCourseRequest, "UpdateCourseRequest"),
        (CreateClassSessionRequest, "CreateClassSessionRequest"),
        (CreateAccountBindingRequest, "CreateAccountBindingRequest"),
        (AccountBindingResponse, "AccountBinding"),
    )
    for model, contract_name in pairs:
        model_fields = set(model.model_json_schema(by_alias=True)["properties"])
        contract_fields = set(contract_schemas[contract_name]["properties"])
        assert model_fields == contract_fields, contract_name
