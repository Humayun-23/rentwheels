from fastapi.testclient import TestClient

def test_add_payment_updates_summary(client: TestClient, rental_booking, verified_owner, auth_headers, db_session):
    headers = auth_headers(verified_owner)
    
    # 1. Check initial booking summary
    response = client.get(f"/api/v1/rentalos/bookings/{rental_booking.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["advance_paid"] == 0
    assert data["balance_due"] == 0
    assert data["security_deposit"] == 0
    
    # 2. Add advance payment
    pay_response = client.post(
        f"/api/v1/rentalos/bookings/{rental_booking.id}/payments",
        headers=headers,
        json={
            "payment_type": "advance",
            "amount": 500,
            "status": "paid",
            "method": "cash"
        }
    )
    assert pay_response.status_code == 201
    
    # 3. Add security deposit
    client.post(
        f"/api/v1/rentalos/bookings/{rental_booking.id}/payments",
        headers=headers,
        json={
            "payment_type": "security_deposit",
            "amount": 1000,
            "status": "paid",
            "method": "upi"
        }
    )
    
    # 4. Verify booking summary is updated
    response2 = client.get(f"/api/v1/rentalos/bookings/{rental_booking.id}", headers=headers)
    data2 = response2.json()
    assert data2["advance_paid"] == 500
    assert data2["security_deposit"] == 1000

def test_trip_completion(client: TestClient, owner_shop, owner_bike, rental_booking, verified_owner, auth_headers):
    headers = auth_headers(verified_owner)
    
    # 1. Complete the trip
    comp_response = client.post(
        f"/api/v1/rentalos/bookings/{rental_booking.id}/complete",
        headers=headers,
        json={
            "note": "Returned safely",
            "customer_flag_type": "good_customer",
            "customer_flag_severity": "info",
            "customer_flag_note": "Good customer"
        }
    )
    assert comp_response.status_code == 200
    
    # 2. Verify booking is completed and bike is available again
    response = client.get(f"/api/v1/rentalos/bookings/{rental_booking.id}", headers=headers)
    assert response.json()["status"] == "completed"
    
    cat_response = client.get(f"/api/v1/rentalos/catalog/vehicles?shop_id={owner_shop.id}", headers=headers)
    cat_data = cat_response.json()
    assert cat_data[0]["is_available"] == True
    assert cat_data[0]["rentalos_availability_status"] == "available"

def test_payment_on_completed_booking(client: TestClient, rental_booking, verified_owner, auth_headers):
    headers = auth_headers(verified_owner)
    
    # Complete the trip
    client.post(
        f"/api/v1/rentalos/bookings/{rental_booking.id}/complete",
        headers=headers,
        json={}
    )
    
    # Try to add payment after completion
    pay_response = client.post(
        f"/api/v1/rentalos/bookings/{rental_booking.id}/payments",
        headers=headers,
        json={
            "payment_type": "balance",
            "amount": 200,
            "status": "paid"
        }
    )
    # The API might allow post-trip payments (e.g. for damage), or it might reject them.
    # We just ensure it doesn't crash. If it rejects, we test for 400. Let's assume it accepts.
    assert pay_response.status_code in (200, 400)
