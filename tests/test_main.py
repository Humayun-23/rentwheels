from fastapi.testclient import TestClient


def test_read_main(client):
    response = client.get("/")
    assert response.status_code == 200

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200

def test_get_user_profile(client):
    response = client.get("/api/v1/users/profile")
    assert response.status_code == 401