# =====================================================================
# test_booking.py
# 
# This file contains integration tests for the Booking endpoints.
# It tests the core business logic of the bike rental application:
# making sure users can book bikes, dates are validated, and 
# double-booking is prevented.
# =====================================================================

from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from app.utils import tz

# We import our database models so we can manually insert "fake" data
# for our tests to interact with.
from app.db.models import Shop, Bike, BikeInventory, Booking
from tests.test_users import setup_verified_user, get_auth_token

def setup_test_bike(db_session, owner):
    """
    Helper function to create a fake Shop, Bike, and Inventory in the DB.
    This gives our customer something to actually book!
    """
    # 1. Create a Shop
    shop = Shop(
        owner_id=owner.id,
        name="Test Shop",
        phone_number="1234567890",
        address="123 Main St",
        city="Test City"
    )
    db_session.add(shop)
    db_session.commit()
    db_session.refresh(shop)

    # 2. Create a Bike in that Shop
    bike = Bike(
        shop_id=shop.id,
        name="Test Bike",
        model="2024",
        bike_type="scooty",
        price_per_hour=1000,  # Prices are usually in cents/paise
        price_per_day=5000,
        condition="good"
    )
    db_session.add(bike)
    db_session.commit()
    db_session.refresh(bike)

    # 3. Create Inventory for the Bike
    inventory = BikeInventory(
        bike_id=bike.id,
        shop_id=shop.id,
        total_quantity=1,
        available_quantity=1
    )
    db_session.add(inventory)
    db_session.commit()

    return bike


def test_create_booking_success(client, db_session):
    """
    The 'Happy Path': A customer successfully books a bike for available dates.
    """
    # ---------------------------------------------------------
    # STEP 1: DATABASE SETUP
    # ---------------------------------------------------------
    owner = setup_verified_user(db_session, email="owner@example.com")
    owner.user_type = "shop_owner"
    db_session.commit()

    customer = setup_verified_user(db_session, email="customer@example.com")
    
    # Create the fake bike for the customer to rent
    bike = setup_test_bike(db_session, owner)

    # ---------------------------------------------------------
    # STEP 2: AUTHENTICATION
    # ---------------------------------------------------------
    # The customer logs in to get their token
    token = get_auth_token(client, email="customer@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # ---------------------------------------------------------
    # STEP 3: BOOKING REQUEST
    # ---------------------------------------------------------
    # We want to book the bike starting tomorrow, for 3 days
    start_time = tz.now() + timedelta(days=1)
    end_time = start_time + timedelta(days=3)

    booking_data = {
        "bike_id": bike.id,
        "utr_number": "123456789012", # Required 12-digit UPI reference
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat()
    }
    
    response = client.post("/api/v1/bookings/", json=booking_data, headers=headers)
    
    # ---------------------------------------------------------
    # STEP 4: ASSERTIONS
    # ---------------------------------------------------------
    assert response.status_code == 201
    data = response.json()
    
    # Assert the booking is linked to the correct bike
    assert data["bike_id"] == bike.id
    
    # Assert the booking starts in "pending" status (awaiting shop owner approval)
    assert data["status"] == "pending"


def test_create_booking_overlapping_dates_fails(client, db_session):
    """
    The 'Business Logic Path': Ensure a user cannot book a bike if someone 
    else has already booked it for those exact dates (Double Booking Prevention).
    """
    owner = setup_verified_user(db_session, email="owner@example.com")
    owner.user_type = "shop_owner"
    db_session.commit()

    customer1 = setup_verified_user(db_session, email="customer1@example.com")
    customer2 = setup_verified_user(db_session, email="customer2@example.com")
    
    bike = setup_test_bike(db_session, owner)

    # Define the rental period (Tomorrow -> 3 days from now)
    start_time = tz.now() + timedelta(days=1)
    end_time = start_time + timedelta(days=3)

    # ---------------------------------------------------------
    # STEP 1: Customer 1 books the bike successfully
    # ---------------------------------------------------------
    existing_booking = Booking(
        customer_id=customer1.id,
        bike_id=bike.id,
        start_time=start_time,
        end_time=end_time,
        status="confirmed", # Simulate that the shop owner already confirmed it
        utr_number="111111111111"
    )
    db_session.add(existing_booking)
    db_session.commit()

    # ---------------------------------------------------------
    # STEP 2: Customer 2 tries to book the SAME bike for the SAME dates
    # ---------------------------------------------------------
    token2 = get_auth_token(client, email="customer2@example.com")
    headers2 = {"Authorization": f"Bearer {token2}"}

    booking_data = {
        "bike_id": bike.id,
        "utr_number": "222222222222",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat()
    }
    
    response = client.post("/api/v1/bookings/", json=booking_data, headers=headers2)
    
    # ---------------------------------------------------------
    # STEP 3: Assert the backend blocks the double-booking!
    # ---------------------------------------------------------
    # A 400 Bad Request (or 409 Conflict) should be returned by your API
    # because the bike is unavailable.
    assert response.status_code == 400
    assert "fully booked" in response.json()["detail"].lower()
