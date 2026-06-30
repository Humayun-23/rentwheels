from datetime import timedelta

from fastapi.testclient import TestClient

from app.db.models import Bike, RentalBooking, RentalCustomer
from app.utils import tz


def create_customer(db_session, shop_id: int, phone: str) -> RentalCustomer:
    customer = RentalCustomer(
        shop_id=shop_id,
        phone_number=phone,
        firstname="History",
        lastname="Customer",
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


def create_bike(db_session, shop_id: int, name: str) -> Bike:
    bike = Bike(
        shop_id=shop_id,
        name=name,
        model="Filter Model",
        bike_type="scooty",
        price_per_hour=100,
        price_per_day=1000,
        is_available=True,
    )
    db_session.add(bike)
    db_session.commit()
    db_session.refresh(bike)
    return bike


def create_booking(db_session, shop_id: int, customer_id: int, bike_id: int, hours_from_now: int) -> RentalBooking:
    start_time = tz.now() + timedelta(hours=hours_from_now)
    booking = RentalBooking(
        shop_id=shop_id,
        customer_id=customer_id,
        bike_id=bike_id,
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        status="confirmed",
        total_amount=500,
        advance_paid=100,
        balance_due=400,
        security_deposit=0,
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)
    return booking


def test_list_rental_bookings_can_filter_by_customer_id(
    client: TestClient,
    db_session,
    owner_shop,
    owner_bike,
    rental_customer,
    verified_owner,
    auth_headers,
):
    other_customer = create_customer(db_session, owner_shop.id, "5555550002")
    target_booking = create_booking(db_session, owner_shop.id, rental_customer.id, owner_bike.id, 3)
    other_booking = create_booking(db_session, owner_shop.id, other_customer.id, owner_bike.id, 6)

    response = client.get(
        f"/api/v1/rentalos/bookings?shop_id={owner_shop.id}&customer_id={rental_customer.id}",
        headers=auth_headers(verified_owner),
    )

    assert response.status_code == 200
    booking_ids = [booking["id"] for booking in response.json()]
    assert booking_ids == [target_booking.id]
    assert other_booking.id not in booking_ids


def test_list_rental_bookings_customer_filter_does_not_cross_shop_leak(
    client: TestClient,
    db_session,
    owner_shop,
    other_shop,
    verified_owner,
    auth_headers,
):
    other_customer = create_customer(db_session, other_shop.id, "5555550003")
    other_bike = create_bike(db_session, other_shop.id, "Other Shop Bike")
    create_booking(db_session, other_shop.id, other_customer.id, other_bike.id, 4)

    response = client.get(
        f"/api/v1/rentalos/bookings?shop_id={owner_shop.id}&customer_id={other_customer.id}",
        headers=auth_headers(verified_owner),
    )

    assert response.status_code == 200
    assert response.json() == []


def test_list_rental_bookings_unfiltered_behavior_still_returns_shop_bookings(
    client: TestClient,
    db_session,
    owner_shop,
    owner_bike,
    rental_customer,
    verified_owner,
    auth_headers,
):
    second_customer = create_customer(db_session, owner_shop.id, "5555550004")
    first_booking = create_booking(db_session, owner_shop.id, rental_customer.id, owner_bike.id, 3)
    second_booking = create_booking(db_session, owner_shop.id, second_customer.id, owner_bike.id, 6)

    response = client.get(
        f"/api/v1/rentalos/bookings?shop_id={owner_shop.id}",
        headers=auth_headers(verified_owner),
    )

    assert response.status_code == 200
    booking_ids = {booking["id"] for booking in response.json()}
    assert {first_booking.id, second_booking.id}.issubset(booking_ids)
