from fastapi.testclient import TestClient
from app.db.models import User
from app.utils.utils import hash_password

def setup_verified_user(db_session, email="customer@example.com", user_id=None):
    hashed = hash_password("strongpassword123")
    user = User(
        email=email,
        password=hashed,
        firstname="John",
        lastname="Doe",
        phone_number="1234567890",
        user_type="customer",
        is_email_verified=True,
    )
    if user_id:
        user.id = user_id
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def get_auth_token(client, email="customer@example.com", password="strongpassword123"):
    """Helper function to log in and get an access token."""
    response = client.post("/api/v1/login", data={
        "username": email,
        "password": password,
    })
    return response.json()["access_token"]


def test_get_user_profile_success(client, db_session):

    user = setup_verified_user(db_session)

    token = get_auth_token(client)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get(f"/api/v1/users/{user.id}", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "customer@example.com"
    assert data["id"] == user.id


def test_get_user_profile_unauthenticated(client, db_session):
    # 1. Create a user
    user = setup_verified_user(db_session)
    
    # 2. Request the user profile WITHOUT a token
    response = client.get(f"/api/v1/users/{user.id}")
    
    # Should be rejected
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_get_user_profile_forbidden(client, db_session):
    user1 = setup_verified_user(db_session, email="user1@example.com")
    user2 = setup_verified_user(db_session, email="user2@example.com")
    
    token1 = get_auth_token(client, email="user1@example.com")
    
    headers = {"Authorization": f"Bearer {token1}"}
    response = client.get(f"/api/v1/users/{user2.id}", headers=headers)
    
    assert response.status_code == 403
    assert response.json()["detail"] == "You can only access your own profile"
