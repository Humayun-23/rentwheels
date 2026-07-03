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


def _content_matches_type(content: bytes, content_type: str) -> bool:
    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    if content_type == "application/pdf":
        return content.startswith(b"%PDF-")
    return False


def _create_r2_client():
    if not all([settings.r2_account_id, settings.r2_access_key_id, settings.r2_secret_access_key, settings.r2_bucket_name]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudflare R2 Storage is not fully configured.",
        )

    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="boto3 is not installed.",
        ) from exc

    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def validate_rentalos_upload(file: UploadFile, allowed_content_types: set[str], max_size_bytes: int) -> bytes:
    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}",
        )

    if file.size and file.size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds the {settings.rentalos_max_upload_mb}MB limit.",
        )

    data = file.file.read()
    if len(data) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds the {settings.rentalos_max_upload_mb}MB limit.",
        )

    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if not _content_matches_type(data, file.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file content does not match the declared file type.",
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
    try:
        s3 = _create_r2_client()
        s3.put_object(
            Bucket=settings.r2_bucket_name,
            Key=blob_name,
            Body=content,
            ContentType=content_type,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("RentalOS Cloudflare R2 upload failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RentalOS file upload failed.",
        ) from exc

    return RentalOSBlobUpload(blob_name=blob_name, blob_url=blob_name)


def generate_rentalos_presigned_url(blob_name: str) -> str:
    try:
        s3 = _create_r2_client()
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.r2_bucket_name, "Key": blob_name},
            ExpiresIn=settings.rentalos_r2_presigned_expire_seconds,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("RentalOS Cloudflare R2 signed URL generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RentalOS file download link generation failed.",
        ) from exc
