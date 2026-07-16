from fastapi.testclient import TestClient

def test_login_success(client: TestClient):
    response = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_create_and_list_members(client: TestClient, auth_headers: dict):
    # Create member
    member_data = {
        "name": "John Doe",
        "phone": "1234567890",
        "join_date": "2023-01-01",
        "gender": "male"
    }
    response = client.post("/members", json=member_data, headers=auth_headers)
    assert response.status_code == 201
    created_member = response.json()
    assert created_member["name"] == "John Doe"
    assert created_member["status"] == "normal"

    # List members
    response = client.get("/members", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(m["phone"] == "1234567890" for m in data["items"])

def test_create_and_list_card_products(client: TestClient, auth_headers: dict):
    # Create card product
    card_data = {
        "name": "Monthly Pass",
        "card_type": "duration",
        "price": "500.00",
        "valid_days": 30,
        "activation_mode": "immediate",
        "applicable_course_scope": "group",
        "absence_deduct_enabled": False,
        "cancel_refund_enabled": False
    }
    response = client.post("/card-products", json=card_data, headers=auth_headers)
    assert response.status_code == 201
    created_card = response.json()
    assert created_card["name"] == "Monthly Pass"

    # List card products
    response = client.get("/card-products", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(c["name"] == "Monthly Pass" for c in data["items"])
