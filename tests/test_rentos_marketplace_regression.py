import hashlib
import hmac
from datetime import timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.db.models import BikeInventory, Booking, Payment, RentalBooking, RentalPayment
from app.utils import tz
from app.utils.limiter import limiter


def test_customer_books_vehicle_from_marketplace_end_to_end(
    monkeypatch,
    client: TestClient,
    db_session,
    owner_bike,
    verified_customer,
    verified_owner,
    auth_headers,
):
    limiter.reset()
    monkeypatch.setattr("app.utils.email.send_email_background", lambda *args, **kwargs: None)

    marketplace_response = client.get(
        "/api/v1/search/vehicles",
        params={
            "vehicle_type": owner_bike.bike_type,
            "is_available": True,
            "shop_id": owner_bike.shop_id,
        },
    )

    assert marketplace_response.status_code == 200
    marketplace_vehicles = marketplace_response.json()
    assert any(vehicle["id"] == owner_bike.id for vehicle in marketplace_vehicles)

    detail_response = client.get(f"/api/v1/bikes/{owner_bike.id}/full-details")

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["vehicle"]["id"] == owner_bike.id
    assert detail["availability"] == {
        "bike_id": owner_bike.id,
        "is_available": True,
        "available_count": 1,
        "total_count": 1,
    }

    headers = auth_headers(verified_customer)
    start_time = tz.now() + timedelta(days=1)
    end_time = start_time + timedelta(hours=2)

    booking_response = client.post(
        "/api/v1/bookings/",
        headers=headers,
        json={
            "bike_id": owner_bike.id,
            "utr_number": "123456789012",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )

    assert booking_response.status_code == 201
    booking_payload = booking_response.json()
    assert booking_payload["customer_id"] == verified_customer.id
    assert booking_payload["bike_id"] == owner_bike.id
    assert booking_payload["status"] == "pending"
    assert booking_payload["total_price"] == 200
    assert booking_payload["token_amount"] == 299

    booking_id = booking_payload["id"]
    customer_bookings_response = client.get("/api/v1/bookings/user/", headers=headers)

    assert customer_bookings_response.status_code == 200
    customer_booking_ids = [booking["id"] for booking in customer_bookings_response.json()]
    assert booking_id in customer_booking_ids

    booking_detail_response = client.get(f"/api/v1/bookings/{booking_id}", headers=headers)

    assert booking_detail_response.status_code == 200
    assert booking_detail_response.json()["id"] == booking_id

    owner_bookings_response = client.get(
        "/api/v1/bookings/",
        headers=auth_headers(verified_owner),
    )

    assert owner_bookings_response.status_code == 200
    owner_booking_ids = [booking["id"] for booking in owner_bookings_response.json()]
    assert booking_id in owner_booking_ids

    db_session.expire_all()
    booking = db_session.query(Booking).filter(Booking.id == booking_id).first()
    inventory = db_session.query(BikeInventory).filter(BikeInventory.bike_id == owner_bike.id).first()
    assert booking is not None
    assert booking.customer_id == verified_customer.id
    assert booking.bike_id == owner_bike.id
    assert booking.status == "pending"
    assert booking.total_price == 200
    assert booking.utr_number == "123456789012"
    assert inventory.available_quantity == 0
    assert inventory.rented_quantity == 1
    assert db_session.query(RentalBooking).count() == 0
    assert db_session.query(RentalPayment).count() == 0


@patch("app.api.v1.payments._razorpay_request")
def test_marketplace_booking_and_razorpay_payment_do_not_create_rentalos_records(
    mock_razorpay_request,
    monkeypatch,
    client: TestClient,
    db_session,
    owner_bike,
    verified_customer,
    auth_headers,
):
    limiter.reset()
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_contract")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "test_secret")
    monkeypatch.setattr("app.utils.email.send_email_background", lambda *args, **kwargs: None)
    mock_razorpay_request.return_value = {"id": "order_marketplace_regression"}

    headers = auth_headers(verified_customer)
    start_time = tz.now() + timedelta(days=1)
    end_time = start_time + timedelta(hours=2)

    booking_response = client.post(
        "/api/v1/bookings/",
        headers=headers,
        json={
            "bike_id": owner_bike.id,
            "utr_number": "123456789012",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )

    assert booking_response.status_code == 201
    booking_id = booking_response.json()["id"]

    db_session.expire_all()
    booking = db_session.query(Booking).filter(Booking.id == booking_id).first()
    assert booking is not None
    assert booking.customer_id == verified_customer.id
    assert db_session.query(RentalBooking).count() == 0
    assert db_session.query(RentalPayment).count() == 0

    booking.status = "confirmed"
    db_session.commit()

    order_response = client.post(
        "/api/v1/payments/",
        headers=headers,
        json={"booking_id": booking_id},
    )

    assert order_response.status_code == 201
    assert order_response.json() == {
        "order_id": "order_marketplace_regression",
        "amount": booking.total_price * 100,
        "currency": "INR",
        "key_id": "rzp_test_contract",
    }
    mock_razorpay_request.assert_called_once()

    db_session.expire_all()
    payment = db_session.query(Payment).filter(Payment.booking_id == booking_id).first()
    assert payment is not None
    assert payment.order_id == "order_marketplace_regression"
    assert payment.status == "created"
    assert db_session.query(RentalBooking).count() == 0
    assert db_session.query(RentalPayment).count() == 0

    payment_id = "pay_marketplace_regression"
    signature = hmac.new(
        b"test_secret",
        f"{payment.order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    verify_response = client.post(
        "/api/v1/payments/verify",
        headers=headers,
        json={
            "order_id": payment.order_id,
            "payment_id": payment_id,
            "razorpay_signature": signature,
        },
    )

    assert verify_response.status_code == 200
    assert verify_response.json()["message"] == "Payment verified successfully"

    db_session.expire_all()
    paid_booking = db_session.query(Booking).filter(Booking.id == booking_id).first()
    paid_payment = db_session.query(Payment).filter(Payment.booking_id == booking_id).first()
    assert paid_booking.status == "paid"
    assert paid_payment.status == "paid"
    assert paid_payment.payment_id == payment_id
    assert db_session.query(RentalBooking).count() == 0
    assert db_session.query(RentalPayment).count() == 0
