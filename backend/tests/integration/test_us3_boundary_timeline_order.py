from datetime import date
from app.api.deps.business_clock import get_business_today
from app.main import app
from .test_us3_normal_timeline import _member, _purchase, _times_product, _writeoff

TODAY = date(2026, 7, 17)

def test_same_day_cancel_rebook_and_absence_are_stably_ordered(client, auth_headers):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    member = _member(client, auth_headers, "13800004701")
    product = _times_product(client, auth_headers, name="边界次卡", total_times=4, valid_days=60)
    _purchase(client, auth_headers, member["id"], product["id"], "us3-boundary-purchase")
    for ref, terminal in (("booking-us3-a", "cancel_refund"), ("booking-us3-b", "absence_commit")):
        assert _writeoff(client, auth_headers, member["id"], ref, "reserve_hold", f"{ref}-reserve").status_code == 200
        assert _writeoff(client, auth_headers, member["id"], ref, terminal, f"{ref}-terminal").status_code == 200
    response = client.get(f"/members/{member['id']}/timeline", params={"category": "writeoff", "dateFrom": TODAY.isoformat(), "dateTo": TODAY.isoformat()}, headers=auth_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 4
    for business_ref in ("booking-us3-a", "booking-us3-b"):
        assert [item["sequenceNo"] for item in items if item["businessRef"] == business_ref] == [2, 1]

def test_terminal_events_are_mutually_exclusive(client, auth_headers):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    member = _member(client, auth_headers, "13800004702")
    product = _times_product(client, auth_headers, name="终态卡", total_times=2, valid_days=30)
    _purchase(client, auth_headers, member["id"], product["id"], "us3-terminal-purchase")
    _writeoff(client, auth_headers, member["id"], "booking-us3-terminal", "reserve_hold", "us3-terminal-reserve")
    committed = _writeoff(client, auth_headers, member["id"], "booking-us3-terminal", "checkin_commit", "us3-terminal-checkin")
    conflict = _writeoff(client, auth_headers, member["id"], "booking-us3-terminal", "cancel_refund", "us3-terminal-cancel")
    assert committed.status_code == 200 and conflict.status_code == 409

def test_absence_without_deduction_refunds_reserved_time(client, auth_headers):
    app.dependency_overrides[get_business_today] = lambda: TODAY
    member = _member(client, auth_headers, "13800004703")
    product = client.post("/card-products", json={"name": "缺勤不扣卡", "cardType": "times", "price": "300.00", "totalTimes": 2, "validDays": 30, "activationMode": "immediate", "applicableCourseScope": "group", "absenceDeductEnabled": False, "cancelRefundEnabled": True}, headers=auth_headers).json()
    card = _purchase(client, auth_headers, member["id"], product["id"], "us3-absence-purchase")["memberCard"]
    _writeoff(client, auth_headers, member["id"], "booking-us3-absence", "reserve_hold", "us3-absence-reserve")
    absent = _writeoff(client, auth_headers, member["id"], "booking-us3-absence", "absence_commit", "us3-absence-terminal")
    assert absent.status_code == 200 and absent.json()["timesDelta"] == 1
    cards = client.get(f"/members/{member['id']}/cards", headers=auth_headers).json()["items"]
    updated = next(item for item in cards if item["id"] == card["id"])
    assert updated["remainingTimes"] == 2 and updated["usedTimes"] == 0
