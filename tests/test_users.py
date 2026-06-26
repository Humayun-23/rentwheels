from fastapi.testclient import TestClient

def test_get_user_profile_success(client: TestClient, verified_customer, auth_headers):
    headers = auth_headers(verified_customer)
    response = client.get(f"/api/v1/users/{verified_customer.id}", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == verified_customer.email
    assert data["id"] == verified_customer.id

def test_get_user_profile_unauthenticated(client: TestClient, verified_customer):
    response = client.get(f"/api/v1/users/{verified_customer.id}")
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

def test_get_user_profile_forbidden(client: TestClient, verified_customer, auth_headers, db_session):
    from tests.conftest import create_test_user
    user2 = create_test_user(db_session, "user2@example.com", "customer")
    
    headers = auth_headers(verified_customer)
    response = client.get(f"/api/v1/users/{user2.id}", headers=headers)
    
    assert response.status_code == 403
    assert response.json()["detail"] == "You can only access your own profile"
