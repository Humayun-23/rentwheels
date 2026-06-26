from fastapi.testclient import TestClient
import pytest

def test_catalog_access_owner(client: TestClient, owner_shop, verified_owner, auth_headers):
    # Owner accesses their own shop catalog -> 200
    headers = auth_headers(verified_owner)
    response = client.get(f"/api/v1/rentalos/catalog/vehicles?shop_id={owner_shop.id}", headers=headers)
    assert response.status_code == 200

def test_catalog_access_other_owner(client: TestClient, owner_shop, other_owner, auth_headers):
    # Other owner tries to access first owner's catalog -> 403
    headers = auth_headers(other_owner)
    response = client.get(f"/api/v1/rentalos/catalog/vehicles?shop_id={owner_shop.id}", headers=headers)
    assert response.status_code == 403

def test_catalog_access_active_staff(client: TestClient, owner_shop, rental_staff, auth_headers):
    # Active staff accesses their assigned shop catalog -> 200
    # rental_staff fixture binds staff_user to owner_shop
    headers = auth_headers(rental_staff.user)
    response = client.get(f"/api/v1/rentalos/catalog/vehicles?shop_id={owner_shop.id}", headers=headers)
    assert response.status_code == 200

def test_catalog_access_inactive_staff(client: TestClient, owner_shop, inactive_rental_staff, auth_headers):
    # Inactive staff tries to access assigned shop catalog -> 403
    headers = auth_headers(inactive_rental_staff.user)
    response = client.get(f"/api/v1/rentalos/catalog/vehicles?shop_id={owner_shop.id}", headers=headers)
    assert response.status_code == 403

def test_catalog_access_non_staff_customer(client: TestClient, owner_shop, verified_customer, auth_headers):
    # Regular customer tries to access shop catalog -> 403
    headers = auth_headers(verified_customer)
    response = client.get(f"/api/v1/rentalos/catalog/vehicles?shop_id={owner_shop.id}", headers=headers)
    assert response.status_code == 403

def test_booking_access_isolation(client: TestClient, rental_booking, verified_owner, other_owner, auth_headers):
    # Verified owner accesses their booking -> 200
    headers = auth_headers(verified_owner)
    response = client.get(f"/api/v1/rentalos/bookings/{rental_booking.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == rental_booking.id

    # Other owner accesses the booking -> 403
    headers_other = auth_headers(other_owner)
    response_other = client.get(f"/api/v1/rentalos/bookings/{rental_booking.id}", headers=headers_other)
    assert response_other.status_code == 403
