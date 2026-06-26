from fastapi.testclient import TestClient
from datetime import timedelta
from app.utils import tz
from app.db.models import Booking

def test_catalog_maintenance_status(client: TestClient, owner_shop, owner_bike, verified_owner, auth_headers, db_session):
    headers = auth_headers(verified_owner)
    
    # 1. Bike is available
    response = client.get(f"/api/v1/rentalos/catalog/vehicles?shop_id={owner_shop.id}", headers=headers)
    data = response.json()
    assert len(data) == 1
    assert data[0]["is_available"] == True
    
    # 2. Set maintenance
    owner_bike.maintenance_status = "repair"
    owner_bike.is_available = False
    db_session.commit()
    
    response = client.get(f"/api/v1/rentalos/catalog/vehicles?shop_id={owner_shop.id}", headers=headers)
    data = response.json()
    assert data[0]["is_available"] == False

def test_online_paid_booking_conflict(client: TestClient, owner_shop, owner_bike, rental_customer, verified_owner, auth_headers, db_session, verified_customer):
    headers = auth_headers(verified_owner)
    now = tz.now()
    
    # Create an online PAID booking
    online = Booking(
        customer_id=verified_customer.id,
        bike_id=owner_bike.id,
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=3),
        status="paid",
        total_price=500
    )
    db_session.add(online)
    db_session.commit()
    
    # Try to create a RentalOS booking that overlaps
    response = client.post(
        "/api/v1/rentalos/bookings",
        headers=headers,
        json={
            "shop_id": owner_shop.id,
            "phone_number": rental_customer.phone_number,
            "bike_id": owner_bike.id,
            "start_time": (now + timedelta(hours=2)).isoformat(),
            "end_time": (now + timedelta(hours=4)).isoformat()
        }
    )
    
    # Should be rejected with 400 conflict
    assert response.status_code == 409
    assert "already booked" in response.json()["detail"].lower()
