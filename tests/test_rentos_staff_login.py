from fastapi.testclient import TestClient

from app.db.models import User
from app.utils.limiter import limiter


def test_shop_staff_created_by_owner_can_login(
    client: TestClient,
    db_session,
    owner_shop,
    verified_owner,
    auth_headers,
):
    limiter.reset()
    staff_password = "strongpassword123"
    owner_headers = auth_headers(verified_owner)

    create_response = client.post(
        "/api/v1/rentalos/staff",
        headers=owner_headers,
        json={
            "shop_id": owner_shop.id,
            "email": "login-staff@example.com",
            "password": staff_password,
            "firstname": "Login",
            "lastname": "Staff",
            "phone_number": "9222222222",
            "role": "staff",
        },
    )

    assert create_response.status_code == 201
    staff_data = create_response.json()

    staff_user = db_session.query(User).filter(User.id == staff_data["user_id"]).first()
    assert staff_user is not None
    assert staff_user.user_type == "shop_staff"

    login_response = client.post(
        "/api/v1/login",
        data={
            "username": "login-staff@example.com",
            "password": staff_password,
        },
    )

    assert login_response.status_code == 200
    token_data = login_response.json()
    assert token_data["token_type"] == "bearer"
    assert token_data["access_token"]

    staff_headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    me_response = client.get("/api/v1/rentalos/me", headers=staff_headers)

    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["has_rentalos_access"] is True
    assert me_data["user_id"] == staff_user.id
    assert me_data["user_type"] == "shop_staff"
    assert me_data["owned_shops"] == []
    assert me_data["staff_shops"][0]["shop_id"] == owner_shop.id
    assert me_data["staff_shops"][0]["role"] == "staff"
