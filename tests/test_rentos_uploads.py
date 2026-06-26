from fastapi.testclient import TestClient
import pytest
from unittest.mock import patch
import io
from app.utils.rentalos_azure_blob import RentalOSBlobUpload

@patch("app.api.v1.rentalos.upload_rentalos_blob")
def test_upload_booking_document(mock_upload, client: TestClient, owner_shop, rental_booking, verified_owner, auth_headers):
    mock_upload.return_value = RentalOSBlobUpload(
        blob_name="mock_name", 
        blob_url="https://mock.blob.core.windows.net/documents/mock_url.jpg"
    )
    
    headers = auth_headers(verified_owner)
    
    file_content = b"fake image content"
    response = client.post(
        f"/api/v1/rentalos/bookings/{rental_booking.id}/documents",
        headers=headers,
        data={"document_type": "driving_license"},
        files={"file": ("test.jpg", file_content, "image/jpeg")}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["document_type"] == "driving_license"
    assert data["file_url"] == "https://mock.blob.core.windows.net/documents/mock_url.jpg"
    assert data["content_type"] == "image/jpeg"

@patch("app.api.v1.rentalos.upload_rentalos_blob")
def test_upload_booking_document_invalid_type(mock_upload, client: TestClient, rental_booking, verified_owner, auth_headers):
    headers = auth_headers(verified_owner)
    
    file_content = b"fake text content"
    response = client.post(
        f"/api/v1/rentalos/bookings/{rental_booking.id}/documents",
        headers=headers,
        data={"document_type": "driving_license"},
        files={"file": ("test.txt", file_content, "text/plain")}
    )
    
    assert response.status_code == 400
    assert "unsupported file type" in response.json()["detail"].lower()
    
@patch("app.api.v1.rentalos.upload_rentalos_blob")
def test_upload_handover_photo_rejects_pdf(mock_upload, client: TestClient, rental_booking, verified_owner, auth_headers):
    headers = auth_headers(verified_owner)
    
    file_content = b"fake pdf content"
    response = client.post(
        f"/api/v1/rentalos/bookings/{rental_booking.id}/handover-photo",
        headers=headers,
        data={"latitude": 12.34, "longitude": 56.78},
        files={"file": ("test.pdf", file_content, "application/pdf")}
    )
    
    assert response.status_code == 400
    assert "unsupported file type" in response.json()["detail"].lower()

@patch("app.api.v1.rentalos.upload_rentalos_blob")
def test_upload_handover_photo_invalid_location(mock_upload, client: TestClient, rental_booking, verified_owner, auth_headers):
    headers = auth_headers(verified_owner)
    
    file_content = b"fake image content"
    response = client.post(
        f"/api/v1/rentalos/bookings/{rental_booking.id}/handover-photo",
        headers=headers,
        data={"latitude": 91.0, "longitude": 0}, # Invalid latitude
        files={"file": ("test.jpg", file_content, "image/jpeg")}
    )
    
    assert response.status_code == 400 # Pydantic validation error or custom 400
