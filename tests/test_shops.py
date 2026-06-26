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

# We import our custom helper functions from test_users.py. 
# This saves us from rewriting the same "create user" and "login" code in every file!
from tests.test_users import setup_verified_user, get_auth_token

def test_create_shop_as_shop_owner_success(client, db_session):
    """
    Test the "Happy Path": A user with the 'shop_owner' role CAN create a shop.
    """
    # ---------------------------------------------------------
    # STEP 1: DATABASE SETUP (Creating the user)
    # ---------------------------------------------------------
    # We use our helper function to insert a verified user into the database.
    # The `db_session` fixture (from conftest.py) gives us a fresh, isolated database transaction.
    owner = setup_verified_user(db_session, email="owner@example.com", user_id=None)
    
    # By default, setup_verified_user creates a "customer". 
    # Since we are testing shop owner privileges, we manually change the role.
    owner.user_type = "shop_owner"
    
    # We commit the change so it is permanently saved in this test's database transaction.
    db_session.commit()

    # ---------------------------------------------------------
    # STEP 2: AUTHENTICATION (Getting the digital ID card)
    # ---------------------------------------------------------
    # We call the login endpoint using our helper function.
    # This simulates the user typing their email/password into a login form.
    # The backend verifies them and returns a JWT (JSON Web Token).
    token = get_auth_token(client, email="owner@example.com")
    
    # We attach the token to the Authorization header. 
    # The string "Bearer " is required by the OAuth2 standard.
    headers = {"Authorization": f"Bearer {token}"}

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


def test_create_shop_as_customer_forbidden(client, db_session):
    """
    Test the "Negative Path": A user with the 'customer' role CANNOT create a shop.
    This guarantees our security permissions are working.
    """
    # ---------------------------------------------------------
    # STEP 1: DATABASE SETUP
    # ---------------------------------------------------------
    # We create a verified user. Because we don't change `user_type`, 
    # it defaults to "customer".
    customer = setup_verified_user(db_session, email="customer@example.com")

    # ---------------------------------------------------------
    # STEP 2: AUTHENTICATION
    # ---------------------------------------------------------
    # The customer logs in successfully and gets a valid token.
    # (Just because you are logged in doesn't mean you have permission to do everything!)
    token = get_auth_token(client, email="customer@example.com")
    headers = {"Authorization": f"Bearer {token}"}

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
