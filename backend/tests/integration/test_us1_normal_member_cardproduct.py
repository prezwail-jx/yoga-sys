def test_admin_creates_and_queries_member(client, auth_headers):
    payload = {
        "name": "李晨",
        "phone": "13800001234",
        "joinDate": "2026-07-15",
        "gender": "male",
        "emergencyContact": "王芳 13900001111",
    }
    created = client.post("/members", json=payload, headers=auth_headers)
    assert created.status_code == 201
    member = created.json()
    assert member["status"] == "normal"
    assert member["joinDate"] == "2026-07-15"

    result = client.get("/members?keyword=1380000", headers=auth_headers)
    assert result.status_code == 200
    assert result.json()["total"] == 1
    assert result.json()["items"][0]["id"] == member["id"]


def test_admin_creates_and_updates_card_product(client, auth_headers):
    payload = {
        "name": "团课20次卡",
        "cardType": "times",
        "price": "1080.00",
        "totalTimes": 20,
        "validDays": 180,
        "activationMode": "first_booking",
        "applicableCourseScope": "group",
        "absenceDeductEnabled": True,
        "cancelRefundEnabled": True,
    }
    created = client.post("/card-products", json=payload, headers=auth_headers)
    assert created.status_code == 201
    product_id = created.json()["id"]

    updated = client.patch(
        f"/card-products/{product_id}",
        json={"price": "1180.00", "enabled": False},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["price"] == "1180.00"
    assert updated.json()["enabled"] is False


def test_card_product_conditional_fields_are_validated(client, auth_headers):
    response = client.post(
        "/card-products",
        json={
            "name": "错误期限卡",
            "cardType": "duration",
            "price": 100,
            "activationMode": "immediate",
            "applicableCourseScope": "group",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
