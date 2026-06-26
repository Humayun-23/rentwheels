from fastapi.testclient import TestClient

from app.db.models import RentalStaff, User
from app.utils.utils import verify_password


def test_owner_creates_new_staff_and_staff_me_access(
    client: TestClient,
    db_session,
    owner_shop,
    verified_owner,
    auth_headers,
):
    headers = auth_headers(verified_owner)

    response = client.post(
        "/api/v1/rentalos/staff",
        headers=headers,
        json={
            "shop_id": owner_shop.id,
            "email": "counter@example.com",
            "password": "strongpassword123",
            "firstname": "Counter",
            "lastname": "Staff",
            "phone_number": "9999999999",
            "role": "staff",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["shop_id"] == owner_shop.id
    assert data["email"] == "counter@example.com"
    assert data["role"] == "staff"
    assert "password" not in data

    staff_user = db_session.query(User).filter(User.email == "counter@example.com").first()
    assert staff_user is not None
    assert staff_user.user_type == "shop_staff"
    assert staff_user.is_email_verified is True
    assert verify_password("strongpassword123", staff_user.password)

    staff_headers = auth_headers(staff_user)
    profile_response = client.get(f"/api/v1/users/{staff_user.id}", headers=staff_headers)
    assert profile_response.status_code == 200
    assert profile_response.json()["user_type"] == "shop_staff"

    me_response = client.get("/api/v1/rentalos/me", headers=staff_headers)
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["has_rentalos_access"] is True
    assert me_data["owned_shops"] == []
    assert me_data["staff_shops"][0]["shop_id"] == owner_shop.id
    assert me_data["staff_shops"][0]["role"] == "staff"


def test_staff_management_requires_owner(
    client: TestClient,
    owner_shop,
    rental_staff,
    auth_headers,
):
    headers = auth_headers(rental_staff.user)

    response = client.post(
        "/api/v1/rentalos/staff",
        headers=headers,
        json={
            "shop_id": owner_shop.id,
            "email": "newstaff@example.com",
            "password": "strongpassword123",
            "firstname": "New",
            "lastname": "Staff",
            "phone_number": "8888888888",
            "role": "staff",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Only shop owners can manage staff."


def test_owner_cannot_manage_staff_for_another_shop(
    client: TestClient,
    other_shop,
    verified_owner,
    auth_headers,
):
    headers = auth_headers(verified_owner)

    response = client.get(f"/api/v1/rentalos/staff?shop_id={other_shop.id}", headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Only shop owners can manage staff."


def test_duplicate_staff_membership_returns_409(
    client: TestClient,
    owner_shop,
    verified_owner,
    rental_staff,
    auth_headers,
):
    headers = auth_headers(verified_owner)

    response = client.post(
        "/api/v1/rentalos/staff",
        headers=headers,
        json={
            "shop_id": owner_shop.id,
            "email": rental_staff.user.email,
            "firstname": "Existing",
            "lastname": "Staff",
            "phone_number": "7777777777",
            "role": "staff",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "This user is already staff for this shop."


def test_owner_cannot_add_self_as_staff(
    client: TestClient,
    owner_shop,
    verified_owner,
    auth_headers,
):
    headers = auth_headers(verified_owner)

    response = client.post(
        "/api/v1/rentalos/staff",
        headers=headers,
        json={
            "shop_id": owner_shop.id,
            "email": verified_owner.email,
            "firstname": "Owner",
            "lastname": "User",
            "phone_number": "6666666666",
            "role": "staff",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Shop owner does not need a staff membership."


def test_owner_updates_and_deactivates_staff(
    client: TestClient,
    owner_shop,
    verified_owner,
    rental_staff,
    auth_headers,
):
    owner_headers = auth_headers(verified_owner)

    response = client.patch(
        f"/api/v1/rentalos/staff/{rental_staff.id}",
        headers=owner_headers,
        json={
            "firstname": "Updated",
            "phone_number": "5555555555",
            "is_active": False,
            "role": "staff",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["firstname"] == "Updated"
    assert data["phone_number"] == "5555555555"
    assert data["is_active"] is False

    staff_headers = auth_headers(rental_staff.user)
    me_response = client.get("/api/v1/rentalos/me", headers=staff_headers)
    assert me_response.status_code == 200
    assert me_response.json()["has_rentalos_access"] is False
    assert me_response.json()["staff_shops"] == []

    catalog_response = client.get(
        f"/api/v1/rentalos/catalog/vehicles?shop_id={owner_shop.id}",
        headers=staff_headers,
    )
    assert catalog_response.status_code == 403


def test_invalid_staff_role_rejected(
    client: TestClient,
    owner_shop,
    verified_owner,
    auth_headers,
):
    headers = auth_headers(verified_owner)

    response = client.post(
        "/api/v1/rentalos/staff",
        headers=headers,
        json={
            "shop_id": owner_shop.id,
            "email": "manager@example.com",
            "password": "strongpassword123",
            "firstname": "Bad",
            "lastname": "Role",
            "phone_number": "4444444444",
            "role": "manager",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid staff role."


def test_public_signup_cannot_create_shop_staff(client: TestClient):
    response = client.post(
        "/api/v1/users/",
        json={
            "email": "publicstaff@example.com",
            "password": "strongpassword123",
            "firstname": "Public",
            "lastname": "Staff",
            "phone_number": "3333333333",
            "user_type": "shop_staff",
        },
    )

    assert response.status_code == 422
