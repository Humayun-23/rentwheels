import logging
from dataclasses import dataclass
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.config import settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RentalOSBlobUpload:
    blob_name: str
    blob_url: str


CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "application/pdf": "pdf",
}


def validate_rentalos_upload(file: UploadFile, allowed_content_types: set[str], max_size_bytes: int) -> bytes:
    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}",
        )

    if file.size and file.size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds the {settings.azure_storage_rentalos_max_upload_mb}MB limit.",
        )

    data = file.file.read()
    if len(data) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds the {settings.azure_storage_rentalos_max_upload_mb}MB limit.",
        )

    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    return data


def build_rentalos_blob_name(shop_id: int, booking_id: int, folder: str, content_type: str) -> str:
    extension = CONTENT_TYPE_EXTENSIONS.get(content_type)
    if not extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {content_type}",
        )
    return f"rentalos/shops/{shop_id}/bookings/{booking_id}/{folder}/{uuid4().hex}.{extension}"


def upload_rentalos_blob(blob_name: str, content: bytes, content_type: str) -> RentalOSBlobUpload:
    if not settings.azure_storage_connection_string:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Azure Blob Storage is not configured.",
        )
    if not settings.azure_storage_rentalos_container:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RentalOS Azure Blob container is not configured.",
        )

    try:
        from azure.storage.blob import BlobServiceClient, ContentSettings
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Azure Blob Storage SDK is not installed.",
        ) from exc

    try:
        service_client = BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
        blob_client = service_client.get_blob_client(
            container=settings.azure_storage_rentalos_container,
            blob=blob_name,
        )
        blob_client.upload_blob(
            content,
            overwrite=False,
            content_settings=ContentSettings(content_type=content_type),
        )
    except Exception as exc:
        logger.exception("RentalOS Azure Blob upload failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RentalOS file upload failed.",
        ) from exc

    if settings.azure_storage_rentalos_public_base_url:
        base_url = settings.azure_storage_rentalos_public_base_url.rstrip("/")
        blob_url = f"{base_url}/{blob_name}"
    else:
        blob_url = blob_client.url

    return RentalOSBlobUpload(blob_name=blob_name, blob_url=blob_url)
