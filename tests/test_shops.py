# =====================================================================
# test_shops.py
# 
# This file contains integration tests for the Shops endpoints.
# It focuses on Role-Based Access Control (RBAC) to ensure that
# only authorized users ("shop_owner") can create shops.
# =====================================================================

# TestClient acts as a virtual web browser that can send HTTP requests 
# (GET, POST, etc.) directly to our FastAPI application without needing a real server.
from fastapi.testclient import TestClient

# We use our custom fixtures from conftest.py instead of imports.

def test_create_shop_as_shop_owner_success(client, verified_owner, auth_headers):
    """
    Test the "Happy Path": A user with the 'shop_owner' role CAN create a shop.
    """
    # ---------------------------------------------------------
    # STEP 1: DATABASE SETUP (Creating the user)
    # ---------------------------------------------------------
    # The `verified_owner` fixture creates a user with `user_type = "shop_owner"`.

    # ---------------------------------------------------------
    # STEP 2: AUTHENTICATION (Getting the digital ID card)
    # ---------------------------------------------------------
    # We use our fixture to get the auth headers.
    headers = auth_headers(verified_owner)

    # ---------------------------------------------------------
    # STEP 3: API REQUEST (Sending the data)
    # ---------------------------------------------------------
    # This dictionary represents the JSON body that the frontend would send.
    # It must match the fields defined in `ShopCreate` (in app/schemas/shops.py).
    shop_data = {
        "name": "Mountain Bikes RentWheels",
        "description": "Best bikes in town",
        "phone_number": "9876543210",
        "address": "123 Main St",
        "city": "Denver"
    }
    
    # We simulate a POST request to create the shop.
    # We pass BOTH the data payload (json=shop_data) AND our identity (headers=headers).
    response = client.post("/api/v1/shops/", json=shop_data, headers=headers)
    
    # ---------------------------------------------------------
    # STEP 4: ASSERTIONS (Verifying the results)
    # ---------------------------------------------------------
    # `201 Created` is the standard HTTP status code for successfully creating a new resource.
    assert response.status_code == 201
    
    # We convert the backend's JSON response back into a Python dictionary.
    data = response.json()
    
    # We verify that the backend actually saved and returned the name we sent it.
    assert data["name"] == "Mountain Bikes RentWheels"
    assert data["phone_number"] == "9876543210"
    assert data["address"] == "123 Main St"
    assert data["city"] == "Denver"


def test_create_shop_as_customer_forbidden(client, verified_customer, auth_headers):
    """
    Test the "Negative Path": A user with the 'customer' role CANNOT create a shop.
    This guarantees our security permissions are working.
    """
    # ---------------------------------------------------------
    # STEP 1: DATABASE SETUP
    # ---------------------------------------------------------
    # We use the verified_customer fixture.

    # ---------------------------------------------------------
    # STEP 2: AUTHENTICATION
    # ---------------------------------------------------------
    headers = auth_headers(verified_customer)

    # ---------------------------------------------------------
    # STEP 3: HACKING ATTEMPT
    # ---------------------------------------------------------
    # The customer tries to hit the shop creation endpoint, hoping the backend
    # forgot to check their user role.
    shop_data = {
        "name": "Customer's Fake Shop",
        "phone_number": "1112223334",
        "address": "Hackerville",
        "city": "New York"
    }
    
    response = client.post("/api/v1/shops/", json=shop_data, headers=headers)
    
    # ---------------------------------------------------------
    # STEP 4: SECURITY VERIFICATION
    # ---------------------------------------------------------
    # `403 Forbidden` means: "I know who you are (authenticated), but you are not allowed to do this (unauthorized)."
    assert response.status_code == 403
    
    # We ensure the backend provides the correct error message.
    assert response.json()["detail"] == "Only shop owners can create shops"
