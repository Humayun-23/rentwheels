from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.db.models import RentalBooking


AS_OF = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)


def create_summary_booking(
    db_session,
    *,
    shop_id: int,
    customer_id: int,
    bike_id: int,
    start_time: datetime,
    end_time: datetime,
    status: str,
    balance_due: int = 0,
    advance_paid: int = 0,
    created_at: datetime | None = None,
) -> RentalBooking:
    booking = RentalBooking(
        shop_id=shop_id,
        customer_id=customer_id,
        bike_id=bike_id,
        start_time=start_time,
        end_time=end_time,
        status=status,
        total_amount=balance_due + advance_paid,
        advance_paid=advance_paid,
        balance_due=balance_due,
        security_deposit=0,
        created_at=created_at or start_time,
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)
    return booking


def test_dashboard_summary_returns_kpis_without_loading_full_bookings(
    client: TestClient,
    db_session,
    owner_shop,
    owner_bike,
    rental_customer,
    verified_owner,
    auth_headers,
):
    headers = auth_headers(verified_owner)

    create_summary_booking(
        db_session,
        shop_id=owner_shop.id,
        customer_id=rental_customer.id,
        bike_id=owner_bike.id,
        start_time=datetime(2026, 6, 30, 9, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 6, 30, 18, 0, tzinfo=timezone.utc),
        status="active",
        balance_due=400,
        advance_paid=100,
        created_at=datetime(2026, 6, 30, 10, 0, tzinfo=timezone.utc),
    )
    create_summary_booking(
        db_session,
        shop_id=owner_shop.id,
        customer_id=rental_customer.id,
        bike_id=owner_bike.id,
        start_time=datetime(2026, 6, 30, 7, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 6, 30, 10, 0, tzinfo=timezone.utc),
        status="confirmed",
        balance_due=150,
        advance_paid=50,
        created_at=datetime(2026, 6, 30, 9, 0, tzinfo=timezone.utc),
    )
    create_summary_booking(
        db_session,
        shop_id=owner_shop.id,
        customer_id=rental_customer.id,
        bike_id=owner_bike.id,
        start_time=datetime(2026, 6, 29, 7, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 6, 29, 10, 0, tzinfo=timezone.utc),
        status="active",
        balance_due=70,
        advance_paid=30,
        created_at=datetime(2026, 6, 29, 9, 0, tzinfo=timezone.utc),
    )
    create_summary_booking(
        db_session,
        shop_id=owner_shop.id,
        customer_id=rental_customer.id,
        bike_id=owner_bike.id,
        start_time=datetime(2026, 6, 30, 9, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 6, 30, 11, 0, tzinfo=timezone.utc),
        status="cancelled",
        balance_due=999,
        advance_paid=999,
        created_at=datetime(2026, 6, 30, 10, 0, tzinfo=timezone.utc),
    )

    response = client.get(
        "/api/v1/rentalos/dashboard/summary",
        params={"shop_id": owner_shop.id, "as_of": AS_OF.isoformat()},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["active_count"] == 3
    assert data["active_delta"] == 2
    assert data["due_today_count"] == 2
    assert data["due_today_delta"] == 1
    assert data["overdue_count"] == 2
    assert data["overdue_delta"] == 1
    assert data["outstanding"] == 620
    assert data["outstanding_delta"] == 550
    assert data["today_revenue"] == 150
    assert data["revenue_delta"] == 120


def test_dashboard_summary_does_not_cross_shop_leak(
    client: TestClient,
    db_session,
    owner_shop,
    other_shop,
    owner_bike,
    rental_customer,
    verified_owner,
    auth_headers,
):
    create_summary_booking(
        db_session,
        shop_id=other_shop.id,
        customer_id=rental_customer.id,
        bike_id=owner_bike.id,
        start_time=datetime(2026, 6, 30, 9, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 6, 30, 10, 0, tzinfo=timezone.utc),
        status="active",
        balance_due=500,
        advance_paid=500,
        created_at=datetime(2026, 6, 30, 9, 0, tzinfo=timezone.utc),
    )

    response = client.get(
        "/api/v1/rentalos/dashboard/summary",
        params={"shop_id": owner_shop.id, "as_of": AS_OF.isoformat()},
        headers=auth_headers(verified_owner),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["active_count"] == 0
    assert data["outstanding"] == 0
    assert data["today_revenue"] == 0
