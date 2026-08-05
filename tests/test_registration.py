from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

response = client.post("/api/v1/users/", json={
    "firstname": "Test",
    "lastname": "User",
    "email": "test123456@example.com",
    "password": "password123",
    "phone_number": "1234567890",
    "user_type": "customer"
})

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
