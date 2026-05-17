import logging
from fastapi import HTTPException, UploadFile
import cloudinary
import cloudinary.uploader

from app.config import settings

logger = logging.getLogger(__name__)


def upload_image(file: UploadFile, folder: str) -> str:
    if not settings.cloudinary_url:
        raise HTTPException(status_code=500, detail="Cloudinary is not configured")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    cloudinary.config(cloudinary_url=settings.cloudinary_url, secure=True)

    try:
        result = cloudinary.uploader.upload(file.file, folder=folder, resource_type="image")
    except Exception as exc:
        logger.exception("Cloudinary upload failed")
        raise HTTPException(status_code=500, detail="Image upload failed") from exc

    url = result.get("secure_url") or result.get("url")
    if not url:
        raise HTTPException(status_code=500, detail="Image upload failed")
    return url
