from datetime import timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.utils import tz
from app.utils.rentalos_azure_blob import RentalOSBlobUpload


@patch("app.api.v1.rentalos.upload_rentalos_blob")
def test_owner_counter_flow_covers_rentalos_endpoints(
    mock_upload,
    client: TestClient,
    owner_shop,
    owner_bike,
    verified_owner,
    auth_headers,
):
    mock_upload.side_effect = [
        RentalOSBlobUpload(
            blob_name="documents/license.jpg",
            blob_url="https://mock.blob.core.windows.net/rentalos/license.jpg",
        ),
        RentalOSBlobUpload(
            blob_name="handover/photo.jpg",
            blob_url="https://mock.blob.core.windows.net/rentalos/handover.jpg",
        ),
    ]
    headers = auth_headers(verified_owner)
    start_time = tz.now() + timedelta(hours=3)
    end_time = start_time + timedelta(hours=4)

    me_response = client.get("/api/v1/rentalos/me", headers=headers)
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["has_rentalos_access"] is True
    assert me_data["owned_shops"][0]["shop_id"] == owner_shop.id

    catalog_response = client.get(
        "/api/v1/rentalos/catalog/vehicles",
        headers=headers,
        params={
            "shop_id": owner_shop.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )
    assert catalog_response.status_code == 200
    catalog_data = catalog_response.json()
    assert catalog_data[0]["bike_id"] == owner_bike.id
    assert catalog_data[0]["rentalos_availability_status"] == "available"

    missing_customer_response = client.get(
        f"/api/v1/rentalos/customers/search?shop_id={owner_shop.id}&phone=7000000000",
        headers=headers,
    )
    assert missing_customer_response.status_code == 200
    assert missing_customer_response.json()["found"] is False

    customer_response = client.post(
        "/api/v1/rentalos/customers",
        headers=headers,
        json={
            "shop_id": owner_shop.id,
            "phone_number": "7000000000",
            "firstname": "Walkin",
            "lastname": "Customer",
            "document_consent": True,
            "marketing_consent": False,
        },
    )
    assert customer_response.status_code == 201
    customer_data = customer_response.json()
    assert customer_data["shop_id"] == owner_shop.id
    assert customer_data["document_consent"] is True

    found_customer_response = client.get(
        f"/api/v1/rentalos/customers/search?shop_id={owner_shop.id}&phone=7000000000",
        headers=headers,
    )
    assert found_customer_response.status_code == 200
    assert found_customer_response.json()["found"] is True
    assert found_customer_response.json()["previous_booking_count"] == 0

    booking_response = client.post(
        "/api/v1/rentalos/bookings",
        headers=headers,
        json={
            "shop_id": owner_shop.id,
            "bike_id": owner_bike.id,
            "phone_number": "7000000000",
            "firstname": "Walkin",
            "lastname": "Customer",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_amount": 1200,
            "advance_paid": 200,
            "balance_due": 1000,
            "security_deposit": 500,
            "notes": "Counter booking created.",
        },
    )
    assert booking_response.status_code == 201
    booking_data = booking_response.json()
    booking_id = booking_data["id"]
    assert booking_data["status"] == "confirmed"
    assert booking_data["customer"]["id"] == customer_data["id"]
    assert booking_data["bike"]["id"] == owner_bike.id

    bookings_response = client.get(
        "/api/v1/rentalos/bookings",
        headers=headers,
        params={
            "shop_id": owner_shop.id,
            "status": "confirmed",
            "start_date": (start_time - timedelta(minutes=1)).isoformat(),
            "end_date": (end_time + timedelta(minutes=1)).isoformat(),
        },
    )
    assert bookings_response.status_code == 200
    assert [booking["id"] for booking in bookings_response.json()] == [booking_id]

    detail_response = client.get(f"/api/v1/rentalos/bookings/{booking_id}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == booking_id

    notes_response = client.get(f"/api/v1/rentalos/bookings/{booking_id}/notes", headers=headers)
    assert notes_response.status_code == 200
    assert notes_response.json()[0]["note"] == "Counter booking created."

    add_note_response = client.post(
        f"/api/v1/rentalos/bookings/{booking_id}/notes",
        headers=headers,
        json={"note": "Customer requested helmet."},
    )
    assert add_note_response.status_code == 201

    payment_response = client.post(
        f"/api/v1/rentalos/bookings/{booking_id}/payments",
        headers=headers,
        json={
            "payment_type": "balance",
            "amount": 300,
            "status": "paid",
            "method": "upi",
            "reference_number": "UPI123",
        },
    )
    assert payment_response.status_code == 201
    assert payment_response.json()["received_by_user_id"] == verified_owner.id

    payments_response = client.get(f"/api/v1/rentalos/bookings/{booking_id}/payments", headers=headers)
    assert payments_response.status_code == 200
    assert payments_response.json()[0]["payment_type"] == "balance"

    updated_detail_response = client.get(f"/api/v1/rentalos/bookings/{booking_id}", headers=headers)
    assert updated_detail_response.json()["balance_due"] == 700

    document_response = client.post(
        f"/api/v1/rentalos/bookings/{booking_id}/documents",
        headers=headers,
        data={"document_type": "driving_license"},
        files={"file": ("license.jpg", b"fake image", "image/jpeg")},
    )
    assert document_response.status_code == 201
    assert document_response.json()["file_url"].endswith("/license.jpg")

    documents_response = client.get(f"/api/v1/rentalos/bookings/{booking_id}/documents", headers=headers)
    assert documents_response.status_code == 200
    assert documents_response.json()[0]["document_type"] == "driving_license"

    handover_response = client.post(
        f"/api/v1/rentalos/bookings/{booking_id}/handover-photo",
        headers=headers,
        data={
            "latitude": "12.34",
            "longitude": "56.78",
            "location_accuracy_meters": "10",
            "location_address": "Counter desk",
            "location_permission_granted": "true",
            "captured_at": tz.now().isoformat(),
        },
        files={"file": ("handover.jpg", b"fake image", "image/jpeg")},
    )
    assert handover_response.status_code == 201
    assert handover_response.json()["location_permission_granted"] is True

    handover_list_response = client.get(
        f"/api/v1/rentalos/bookings/{booking_id}/handover-photos",
        headers=headers,
    )
    assert handover_list_response.status_code == 200
    assert handover_list_response.json()[0]["image_url"].endswith("/handover.jpg")

    flag_response = client.post(
        f"/api/v1/rentalos/customers/{customer_data['id']}/flags",
        headers=headers,
        json={
            "flag_type": "watchlist",
            "severity": "warning",
            "note": "Returned late on a previous manual rental.",
            "is_active": True,
        },
    )
    assert flag_response.status_code == 201
    assert flag_response.json()["flag_type"] == "watchlist"

    flags_response = client.get(f"/api/v1/rentalos/customers/{customer_data['id']}/flags", headers=headers)
    assert flags_response.status_code == 200
    assert flags_response.json()[0]["severity"] == "warning"

    flagged_search_response = client.get(
        f"/api/v1/rentalos/customers/search?shop_id={owner_shop.id}&phone=7000000000",
        headers=headers,
    )
    flagged_search_data = flagged_search_response.json()
    assert flagged_search_data["previous_booking_count"] == 1
    assert flagged_search_data["current_flag_status"] == "watchlist"
    assert flagged_search_data["latest_note"] == "Customer requested helmet."

    complete_response = client.post(
        f"/api/v1/rentalos/bookings/{booking_id}/complete",
        headers=headers,
        json={"note": "Trip completed at counter."},
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"


def test_rentalos_me_without_access_returns_empty_access(
    client: TestClient,
    verified_customer,
    auth_headers,
):
    response = client.get("/api/v1/rentalos/me", headers=auth_headers(verified_customer))

    assert response.status_code == 200
    assert response.json()["has_rentalos_access"] is False
    assert response.json()["owned_shops"] == []
    assert response.json()["staff_shops"] == []


def test_rentalos_validation_errors_for_missing_flow_inputs(
    client: TestClient,
    owner_shop,
    owner_bike,
    rental_booking,
    verified_owner,
    auth_headers,
):
    headers = auth_headers(verified_owner)
    now = tz.now()

    partial_catalog_response = client.get(
        "/api/v1/rentalos/catalog/vehicles",
        headers=headers,
        params={"shop_id": owner_shop.id, "start_time": now.isoformat()},
    )
    assert partial_catalog_response.status_code == 400

    invalid_booking_response = client.post(
        "/api/v1/rentalos/bookings",
        headers=headers,
        json={
            "shop_id": owner_shop.id,
            "bike_id": owner_bike.id,
            "phone_number": "7111111111",
            "start_time": now.isoformat(),
            "end_time": (now - timedelta(hours=1)).isoformat(),
        },
    )
    assert invalid_booking_response.status_code == 400

    invalid_payment_response = client.post(
        f"/api/v1/rentalos/bookings/{rental_booking.id}/payments",
        headers=headers,
        json={
            "payment_type": "balance",
            "amount": 0,
            "status": "paid",
            "method": "cash",
        },
    )
    assert invalid_payment_response.status_code == 400

    empty_note_response = client.post(
        f"/api/v1/rentalos/bookings/{rental_booking.id}/notes",
        headers=headers,
        json={"note": "   "},
    )
    assert empty_note_response.status_code == 400

    invalid_flag_response = client.post(
        f"/api/v1/rentalos/customers/{rental_booking.customer_id}/flags",
        headers=headers,
        json={
            "flag_type": "damage_issue",
            "severity": "warning",
            "note": "",
        },
    )
    assert invalid_flag_response.status_code == 400
