import json
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.api.audit import record_audit


def test_record_audit_json_encodes_state_values():
    session = SimpleNamespace(add=lambda _record: None, flush=lambda: None)
    user = SimpleNamespace(user_id="admin-1", role="admin")
    object_id = uuid4()

    record = record_audit(
        session,
        trace_id="trace-1",
        action="private_slot_create",
        user=user,
        object_type="private_availability",
        object_id=str(object_id),
        after_state={
            "id": object_id,
            "created_at": datetime(2030, 1, 1, 9, 0, tzinfo=timezone.utc),
            "opened_on": date(2030, 1, 1),
            "price": Decimal("100.50"),
        },
    )

    json.dumps(record.after_state)
    assert record.after_state == {
        "id": str(object_id),
        "created_at": "2030-01-01T09:00:00+00:00",
        "opened_on": "2030-01-01",
        "price": 100.5,
    }
