from fastapi.testclient import TestClient
from app.db.models import User
from app.utils.utils import hash_password

def test_register_customer(client):
    response = client.post("/api/v1/users/", json={
        "email": "customer@example.com",
        "password": "strongpassword123",
        "firstname": "John",
        "lastname": "Doe",
        "phone_number": "1234567890",
        "user_type": "customer",
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "customer@example.com"
    assert data["user_type"] == "customer" 


def test_register_shop_owner(client):
    response = client.post("/api/v1/users/", json={
        "email": "owner@example.com",
        "password": "strongpassword123",
        "firstname": "Jane",
        "lastname": "Smith",
        "phone_number": "0987654321",
        "user_type": "shop_owner",
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "owner@example.com"
    assert data["user_type"] == "shop_owner"

def test_login_customer(client, db_session):
    hashed = hash_password("strongpassword123")
    user = User(
        email="customer@example.com",
        password=hashed,
        firstname="John",
        lastname="Doe",
        phone_number="1234567890",
        user_type="customer",
        is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    response = client.post("/api/v1/login", data={
        "username": "customer@example.com",
        "password": "strongpassword123",
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

