from fastapi.testclient import TestClient


def assert_required_keys(payload: dict, keys: set[str]) -> None:
    assert keys.issubset(payload.keys())


def test_rentalos_me_response_contract(
    client: TestClient,
    owner_shop,
    verified_owner,
    auth_headers,
):
    response = client.get("/api/v1/rentalos/me", headers=auth_headers(verified_owner))

    assert response.status_code == 200
    data = response.json()
    assert_required_keys(
        data,
        {
            "has_rentalos_access",
            "user_id",
            "email",
            "user_type",
            "owned_shops",
            "staff_shops",
        },
    )
    assert data["has_rentalos_access"] is True
    assert data["user_id"] == verified_owner.id
    assert data["user_type"] == "shop_owner"

    owned_shop = data["owned_shops"][0]
    assert_required_keys(
        owned_shop,
        {"shop_id", "shop_name", "role", "staff_id", "is_active"},
    )
    assert owned_shop["shop_id"] == owner_shop.id
    assert owned_shop["role"] == "owner"
    assert owned_shop["is_active"] is True


def test_rental_staff_response_contract(
    client: TestClient,
    owner_shop,
    verified_owner,
    auth_headers,
):
    response = client.post(
        "/api/v1/rentalos/staff",
        headers=auth_headers(verified_owner),
        json={
            "shop_id": owner_shop.id,
            "email": "frontend-contract-staff@example.com",
            "password": "strongpassword123",
            "firstname": "Frontend",
            "lastname": "Staff",
            "phone_number": "9333333333",
            "role": "staff",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert_required_keys(
        data,
        {
            "id",
            "shop_id",
            "user_id",
            "email",
            "firstname",
            "lastname",
            "phone_number",
            "role",
            "is_active",
            "created_at",
            "updated_at",
        },
    )
    assert "password" not in data
    assert data["shop_id"] == owner_shop.id
    assert data["email"] == "frontend-contract-staff@example.com"
    assert data["role"] == "staff"
    assert data["is_active"] is True


def test_rental_booking_response_contract(
    client: TestClient,
    rental_booking,
    verified_owner,
    auth_headers,
):
    response = client.get(
        f"/api/v1/rentalos/bookings/{rental_booking.id}",
        headers=auth_headers(verified_owner),
    )

    assert response.status_code == 200
    data = response.json()
    assert_required_keys(
        data,
        {
            "id",
            "shop_id",
            "customer_id",
            "bike_id",
            "start_time",
            "end_time",
            "status",
            "total_amount",
            "advance_paid",
            "balance_due",
            "security_deposit",
            "created_at",
            "customer",
            "bike",
        },
    )
    assert data["id"] == rental_booking.id
    assert data["status"] == rental_booking.status

    assert_required_keys(
        data["customer"],
        {"id", "phone_number", "firstname", "lastname", "current_flag_status"},
    )
    assert_required_keys(
        data["bike"],
        {"id", "name", "model", "bike_type"},
    )
