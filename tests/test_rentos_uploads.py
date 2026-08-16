from fastapi.testclient import TestClient
import pytest
from unittest.mock import patch
from fastapi import HTTPException

from app.db.models import RentalBookingDocument
from app.utils import rentalos_r2
from app.utils.rentalos_r2 import RentalOSBlobUpload


JPEG_BYTES = b"\xff\xd8\xff\xe0fake image content"


@patch("app.api.v1.rentalos.documents.generate_rentalos_presigned_url")
@patch("app.api.v1.rentalos.documents.upload_rentalos_blob")
def test_upload_booking_document(
    mock_upload,
    mock_generate_url,
    client: TestClient,
    db_session,
    owner_shop,
    rental_booking,
    verified_owner,
    auth_headers,
):
    mock_generate_url.return_value = "https://mock.blob.core.windows.net/documents/mock_url.jpg"
    mock_upload.return_value = RentalOSBlobUpload(
        blob_name="mock_name", 
        blob_url="https://mock.blob.core.windows.net/documents/mock_url.jpg"
    )
    
    headers = auth_headers(verified_owner)
    
    response = client.post(
        f"/api/v1/rentalos/bookings/{rental_booking.id}/documents",
        headers=headers,
        data={"document_type": "driving_license"},
        files={"file": ("test.jpg", JPEG_BYTES, "image/jpeg")}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["document_type"] == "driving_license"
    assert data["file_url"] == "https://mock.blob.core.windows.net/documents/mock_url.jpg"
    assert data["content_type"] == "image/jpeg"

    db_document = (
        db_session.query(RentalBookingDocument)
        .filter(RentalBookingDocument.booking_id == rental_booking.id)
        .one()
    )
    assert db_document.document_type == "driving_license"
    assert db_document.file_url == "https://mock.blob.core.windows.net/documents/mock_url.jpg"
    assert db_document.file_name == "test.jpg"
    assert db_document.content_type == "image/jpeg"
    assert db_document.uploaded_by_user_id == verified_owner.id

@patch("app.api.v1.rentalos.documents.upload_rentalos_blob")
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


@patch("app.api.v1.rentalos.documents.upload_rentalos_blob")
def test_upload_booking_document_rejects_mime_spoof(mock_upload, client: TestClient, rental_booking, verified_owner, auth_headers):
    headers = auth_headers(verified_owner)

    response = client.post(
        f"/api/v1/rentalos/bookings/{rental_booking.id}/documents",
        headers=headers,
        data={"document_type": "driving_license"},
        files={"file": ("test.jpg", b"not really a jpeg", "image/jpeg")}
    )

    assert response.status_code == 400
    assert "does not match" in response.json()["detail"].lower()
    mock_upload.assert_not_called()


@patch("app.api.v1.rentalos.documents.upload_rentalos_blob")
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

@patch("app.api.v1.rentalos.documents.upload_rentalos_blob")
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


def test_r2_upload_preserves_original_file_bytes(monkeypatch):
    captured = {}

    class FakeR2Client:
        def put_object(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(rentalos_r2, "_create_r2_client", lambda: FakeR2Client())
    monkeypatch.setattr(rentalos_r2.settings, "r2_bucket_name", "test-bucket")

    rentalos_r2.upload_rentalos_blob("documents/test.pdf", b"%PDF-test", "application/pdf")

    assert captured["Bucket"] == "test-bucket"
    assert captured["Key"] == "documents/test.pdf"
    assert captured["Body"] == b"%PDF-test"
    assert captured["ContentType"] == "application/pdf"
    assert "ContentEncoding" not in captured


def test_r2_presigned_url_uses_configured_short_expiry(monkeypatch):
    captured = {}

    class FakeR2Client:
        def generate_presigned_url(self, operation, Params, ExpiresIn):
            captured.update(operation=operation, Params=Params, ExpiresIn=ExpiresIn)
            return "https://signed.example/document"

    monkeypatch.setattr(rentalos_r2, "_create_r2_client", lambda: FakeR2Client())
    monkeypatch.setattr(rentalos_r2.settings, "r2_bucket_name", "test-bucket")
    monkeypatch.setattr(rentalos_r2.settings, "rentalos_r2_presigned_expire_seconds", 300)

    url = rentalos_r2.generate_rentalos_presigned_url("documents/test.pdf")

    assert url == "https://signed.example/document"
    assert captured == {
        "operation": "get_object",
        "Params": {"Bucket": "test-bucket", "Key": "documents/test.pdf"},
        "ExpiresIn": 300,
    }


def test_r2_presigned_url_fails_closed(monkeypatch):
    class FakeR2Client:
        def generate_presigned_url(self, operation, Params, ExpiresIn):
            raise RuntimeError("signing failed")

    monkeypatch.setattr(rentalos_r2, "_create_r2_client", lambda: FakeR2Client())

    with pytest.raises(HTTPException) as exc:
        rentalos_r2.generate_rentalos_presigned_url("documents/test.pdf")

    assert exc.value.status_code == 500
    assert "download link" in exc.value.detail.lower()


@patch("app.api.v1.rentalos.documents.generate_rentalos_presigned_url")
@patch("app.api.v1.rentalos.documents.upload_rentalos_blob")
def test_upload_booking_document_normalizes_image_jpg(
    mock_upload,
    mock_generate_url,
    client: TestClient,
    rental_booking,
    verified_owner,
    auth_headers,
):
    mock_generate_url.return_value = "https://signed.example/doc.jpg"
    mock_upload.return_value = RentalOSBlobUpload(blob_name="mock", blob_url="https://signed.example/doc.jpg")
    headers = auth_headers(verified_owner)

    response = client.post(
        f"/api/v1/rentalos/bookings/{rental_booking.id}/documents",
        headers=headers,
        data={"document_type": "driving_license"},
        files={"file": ("photo.jpg", JPEG_BYTES, "image/jpg")}
    )

    assert response.status_code == 201
    assert response.json()["content_type"] == "image/jpeg"


@patch("app.api.v1.rentalos.documents.generate_rentalos_presigned_url")
@patch("app.api.v1.rentalos.documents.upload_rentalos_blob")
def test_upload_handover_photo_supports_plural_route(
    mock_upload,
    mock_generate_url,
    client: TestClient,
    rental_booking,
    verified_owner,
    auth_headers,
):
    mock_generate_url.return_value = "https://signed.example/photo.jpg"
    mock_upload.return_value = RentalOSBlobUpload(blob_name="mock", blob_url="https://signed.example/photo.jpg")
    headers = auth_headers(verified_owner)

    response = client.post(
        f"/api/v1/rentalos/bookings/{rental_booking.id}/handover-photos",
        headers=headers,
        files={"file": ("photo.jpg", JPEG_BYTES, "image/jpeg")}
    )

    assert response.status_code == 201

